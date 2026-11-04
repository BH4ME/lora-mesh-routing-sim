import unittest
from types import SimpleNamespace

from lora_mesh_sim import Node, Packet, RadioConfig, Simulator, build_protocol


class TraceSimulator(Simulator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tx_history = []

    def begin_transmission(self, sender, packet, pending):
        previous = self.metrics.tx_count
        super().begin_transmission(sender, packet, pending)
        if self.metrics.tx_count > previous:
            self.tx_history.append(self.transmissions[-1])


class DropPrimarySimulator(TraceSimulator):
    def try_receive(self, tx, receiver):
        if (tx.packet.flow_id == 2 and tx.packet.kind == "DATA"
                and tx.packet.repair_index is None
                and tx.sender == 0 and receiver == 3):
            return None
        return super().try_receive(tx, receiver)


class DropNominatedCurrentDataSimulator(DropPrimarySimulator):
    def try_receive(self, tx, receiver):
        if (tx.packet.flow_id == 2 and tx.packet.kind == "DATA"
                and tx.packet.repair_index is None
                and tx.sender == 0 and receiver == 2):
            return None
        return super().try_receive(tx, receiver)


class DropSecondFlowDeliverySimulator(DropPrimarySimulator):
    def try_receive(self, tx, receiver):
        if (tx.packet.flow_id == 2 and receiver == 3
                and tx.packet.kind in {"DATA", "FLOOD"}):
            return None
        return super().try_receive(tx, receiver)


class DropMiddleFlowsDeliverySimulator(TraceSimulator):
    def try_receive(self, tx, receiver):
        if (tx.packet.flow_id in {2, 3} and receiver == 3
                and tx.packet.kind in {"DATA", "FLOOD"}):
            return None
        return super().try_receive(tx, receiver)


class DropTrialRecoverySimulator(DropPrimarySimulator):
    def try_receive(self, tx, receiver):
        if (tx.packet.flow_id == 3 and receiver == 3
                and tx.packet.kind == "FLOOD"):
            return None
        return super().try_receive(tx, receiver)


class DropOlderBackupAckSimulator(DropPrimarySimulator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dropped_old_ack = False

    def try_receive(self, tx, receiver):
        if (tx.packet.flow_id == 3 and tx.packet.kind == "DATA"
                and tx.packet.repair_index is None
                and tx.sender == 0 and receiver == 3):
            return None
        if (tx.packet.flow_id == 2 and tx.packet.kind == "ACK"
                and tx.packet.repair_index == 4 and tx.sender == 2
                and receiver == 0
                and not self.dropped_old_ack):
            self.dropped_old_ack = True
            return None
        return super().try_receive(tx, receiver)


class DropTrialAndFourthPrimarySimulator(DropPrimarySimulator):
    def try_receive(self, tx, receiver):
        if (receiver == 3 and tx.packet.kind == "DATA"
                and ((tx.packet.flow_id == 3 and tx.sender == 2)
                     or (tx.packet.flow_id == 4 and tx.sender == 0))):
            return None
        return super().try_receive(tx, receiver)


class DropStaleTrialAndNewPrimarySimulator(DropSecondFlowDeliverySimulator):
    def try_receive(self, tx, receiver):
        if (receiver == 3 and tx.packet.kind == "DATA"
                and ((tx.packet.flow_id == 3 and tx.sender == 0)
                     or (tx.packet.flow_id == 4 and tx.sender == 2)
                     or (tx.packet.flow_id == 6 and tx.sender == 0))):
            return None
        return super().try_receive(tx, receiver)


class NoPastEventSimulator(TraceSimulator):
    def schedule(self, when, event_type, data):
        if when < self.now - 1e-9:
            raise AssertionError("protocol scheduled an event before current time")
        return super().schedule(when, event_type, data)


class MeshEchoDCBTest(unittest.TestCase):
    def test_flood_ack_carries_only_a_physically_decoded_two_hop_nominee(self):
        protocol = build_protocol("meshecho-dcb")
        protocol.flood_base_delay_s = 0.5
        protocol.flood_jitter_s = 0.0
        sim = TraceSimulator(
            [Node(i, i * 10.0, 0.0) for i in range(4)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 3, 1))

        metrics = sim.run(5.0)

        acks = [tx for tx in sim.tx_history
                if tx.sender == 3 and tx.packet.kind == "ACK"]
        self.assertEqual(len(acks), 1)
        self.assertEqual(acks[0].packet.path, (0, 3))
        self.assertEqual(acks[0].packet.backup_relay_id, 2)
        self.assertIsNone(acks[0].packet.backup_epoch_id)
        self.assertEqual(acks[0].packet.wire_size_bytes(32), 19)
        self.assertAlmostEqual(acks[0].start - metrics.flows[1].delivered_at, 2.0)
        self.assertIsNotNone(metrics.flows[1].acked_at)

    def test_accepted_flood_ack_nominates_the_next_direct_r_data(self):
        protocol = build_protocol("meshecho-dcb")
        protocol.flood_base_delay_s = 0.5
        protocol.flood_jitter_s = 0.0
        sim = TraceSimulator(
            [Node(i, i * 10.0, 0.0) for i in range(4)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 3, 1))
        sim.schedule(5.0, "app_send", (0, 3, 2))

        metrics = sim.run(7.0)

        self.assertIsNotNone(metrics.flows[1].acked_at)
        routed = [tx.packet for tx in sim.tx_history
                  if tx.sender == 0 and tx.packet.flow_id == 2
                  and tx.packet.kind == "DATA"]
        self.assertEqual(len(routed), 1)
        self.assertEqual(routed[0].path, (0, 3))
        self.assertEqual(routed[0].backup_relay_id, 2)
        self.assertEqual(routed[0].backup_epoch_id, 1)
        self.assertEqual(routed[0].wire_size_bytes(32), 55)

    def test_same_field_source_fr_control_changes_only_the_discovery_branch(self):
        decisions_by_protocol = {}
        for name in ("meshecho-dcb", "meshecho-dcb-source-fr"):
            protocol = build_protocol(name)
            protocol.flood_base_delay_s = 0.5
            protocol.flood_jitter_s = 0.0
            sim = TraceSimulator(
                [Node(i, i * 10.0, 0.0) for i in range(4)],
                RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
                seed=17, max_hops=6, independent_random_streams=True,
            )
            for flow_id, when in enumerate((1.0, 20.0, 200.0), start=1):
                sim.schedule(when, "app_send", (0, 3, flow_id))
            sim.run(240.0)
            decisions_by_protocol[name] = [
                event["action"] for event in protocol.action_events
                if event["event"] == "decision"
            ]

        self.assertEqual(decisions_by_protocol["meshecho-dcb"], ["F", "R", "D"])
        self.assertEqual(decisions_by_protocol["meshecho-dcb-source-fr"], ["F", "R", "R"])

    def test_source_fr_keeps_dcb_feedback_and_nomination_wire_fields(self):
        observed = {}
        for name in ("meshecho-dcb", "meshecho-dcb-source-fr"):
            protocol = build_protocol(name)
            protocol.flood_base_delay_s = 0.5
            protocol.flood_jitter_s = 0.0
            sim = TraceSimulator(
                [Node(i, i * 10.0, 0.0) for i in range(4)],
                RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
                seed=17, max_hops=6, independent_random_streams=True,
            )
            sim.schedule(1.0, "app_send", (0, 3, 1))
            sim.schedule(5.0, "app_send", (0, 3, 2))
            sim.run(7.0)
            ack = next(tx.packet for tx in sim.tx_history
                       if tx.sender == 3 and tx.packet.kind == "ACK"
                       and tx.packet.flow_id == 1)
            data = next(tx.packet for tx in sim.tx_history
                        if tx.sender == 0 and tx.packet.kind == "DATA"
                        and tx.packet.flow_id == 2)
            observed[name] = (
                ack.path, ack.backup_relay_id, ack.wire_size_bytes(32),
                data.path, data.backup_relay_id, data.backup_epoch_id,
                data.wire_size_bytes(32),
            )

        self.assertEqual(observed["meshecho-dcb-source-fr"], observed["meshecho-dcb"])

    def test_feedback_and_relay_pending_peaks_follow_live_state(self):
        protocol = build_protocol("meshecho-dcb")
        protocol.flood_base_delay_s = 0.5
        protocol.flood_jitter_s = 0.0
        sim = TraceSimulator(
            [Node(i, i * 10.0, 0.0) for i in range(4)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 3, 1))
        sim.schedule(5.0, "app_send", (0, 3, 2))

        sim.run(6.0)

        self.assertEqual(protocol.peak_feedback_windows_by_destination[3], 1)
        self.assertEqual(protocol.peak_pending_backups_by_relay[2], 1)
        self.assertEqual(len(protocol.feedback_windows), 0)
        self.assertEqual(len(protocol.relay_pending), 1)

    def test_certified_nominee_expires_while_the_direct_route_remains_cached(self):
        protocol = build_protocol("meshecho-dcb")
        protocol.flood_base_delay_s = 0.5
        protocol.flood_jitter_s = 0.0
        sim = TraceSimulator(
            [Node(i, i * 10.0, 0.0) for i in range(4)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 3, 1))
        metrics = sim.run(5.0)
        accepted_at = metrics.flows[1].acked_at
        self.assertIsNotNone(accepted_at)
        sim.schedule(accepted_at + 119.0, "app_send", (0, 3, 2))
        sim.schedule(accepted_at + 121.0, "app_send", (0, 3, 3))

        sim.run(accepted_at + 125.0)

        routed = {
            tx.packet.flow_id: tx.packet for tx in sim.tx_history
            if tx.sender == 0 and tx.packet.kind == "DATA"
            and tx.packet.flow_id in {2, 3}
        }
        self.assertEqual(set(routed), {2, 3})
        self.assertEqual(routed[2].path, (0, 3))
        self.assertEqual(routed[2].backup_relay_id, 2)
        self.assertEqual(routed[2].backup_epoch_id, 1)
        self.assertEqual(routed[3].path, (0, 3))
        self.assertIsNone(routed[3].backup_relay_id)
        self.assertIsNone(routed[3].backup_epoch_id)

    def test_nominated_relay_sends_marked_backup_after_current_data_decode(self):
        protocol = build_protocol("meshecho-dcb")
        protocol.flood_base_delay_s = 0.5
        protocol.flood_jitter_s = 0.0
        sim = DropPrimarySimulator(
            [Node(i, i * 10.0, 0.0) for i in range(4)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 3, 1))
        sim.schedule(5.0, "app_send", (0, 3, 2))

        sim.run(10.0)

        initial = next(tx for tx in sim.tx_history
                       if tx.sender == 0 and tx.packet.flow_id == 2
                       and tx.packet.kind == "DATA")
        backups = [tx for tx in sim.tx_history
                   if tx.sender == 2 and tx.packet.flow_id == 2
                   and tx.packet.kind == "DATA"
                   and tx.packet.repair_index == 4]
        self.assertEqual(len(backups), 1)
        self.assertAlmostEqual(backups[0].start - initial.end, 2.0)
        self.assertEqual(backups[0].packet.path, (0, 2, 3))
        self.assertIsNone(backups[0].packet.backup_relay_id)
        self.assertEqual(backups[0].packet.backup_epoch_id, 1)
        self.assertEqual(backups[0].packet.wire_size_bytes(32), 56)
        acks = [tx.packet for tx in sim.tx_history
                if tx.sender == 3 and tx.packet.flow_id == 2
                and tx.packet.kind == "ACK" and tx.packet.repair_index == 4]
        self.assertEqual(len(acks), 1)
        self.assertEqual(acks[0].path, (0, 2, 3))
        self.assertEqual(acks[0].backup_epoch_id, 1)
        self.assertEqual(acks[0].wire_size_bytes(32), 24)

    def test_valid_backup_ack_confirms_flow_before_fixed_f_recovery(self):
        protocol = build_protocol("meshecho-dcb")
        protocol.flood_base_delay_s = 0.5
        protocol.flood_jitter_s = 0.0
        sim = DropPrimarySimulator(
            [Node(i, i * 10.0, 0.0) for i in range(4)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 3, 1))
        sim.schedule(5.0, "app_send", (0, 3, 2))

        metrics = sim.run(22.0)

        initial = next(tx for tx in sim.tx_history
                       if tx.sender == 0 and tx.packet.flow_id == 2
                       and tx.packet.kind == "DATA")
        self.assertIsNotNone(metrics.flows[2].acked_at)
        self.assertLess(metrics.flows[2].acked_at, initial.start + 15.0)
        self.assertEqual(protocol.route_cache[0][3].path, (0, 3))
        self.assertFalse(any(
            tx.sender == 0 and tx.packet.flow_id == 2
            and tx.packet.kind == "FLOOD" and tx.packet.repair_index == 2
            for tx in sim.tx_history
        ))

    def test_accepted_backup_ack_promotes_only_the_candidate_next_route(self):
        observed = {}
        for name in ("meshecho-dcb", "meshecho-dcb-promote"):
            protocol = build_protocol(name)
            protocol.flood_base_delay_s = 0.5
            protocol.flood_jitter_s = 0.0
            sim = DropPrimarySimulator(
                [Node(i, i * 10.0, 0.0) for i in range(4)],
                RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
                seed=17, max_hops=6, independent_random_streams=True,
            )
            for flow_id, when in enumerate((1.0, 5.0, 10.0), start=1):
                sim.schedule(when, "app_send", (0, 3, flow_id))

            metrics = sim.run(13.0)

            self.assertEqual(
                [protocol.flow_data_actions[flow_id] for flow_id in (1, 2, 3)],
                ["F", "R", "R"],
            )
            self.assertTrue(all(metrics.flows[flow_id].acked_at is not None
                                for flow_id in (1, 2, 3)))
            self.assertTrue(any(
                event.get("event") == "dcb_source_ack_rx"
                and event["flow_id"] == 2 and event["accepted"]
                for event in protocol.action_events
            ))
            first_ack = next(
                tx.packet for tx in sim.tx_history
                if tx.sender == 3 and tx.packet.kind == "ACK"
                and tx.packet.flow_id == 1
            )
            direct_r = next(
                tx.packet for tx in sim.tx_history
                if tx.sender == 0 and tx.packet.kind == "DATA"
                and tx.packet.flow_id == 2
            )
            backup_r = next(
                tx.packet for tx in sim.tx_history
                if tx.sender == 2 and tx.packet.kind == "DATA"
                and tx.packet.flow_id == 2 and tx.packet.repair_index == 4
            )
            backup_ack = next(
                tx.packet for tx in sim.tx_history
                if tx.sender == 3 and tx.packet.kind == "ACK"
                and tx.packet.flow_id == 2 and tx.packet.repair_index == 4
            )
            next_r = next(
                tx.packet for tx in sim.tx_history
                if tx.sender == 0 and tx.packet.kind == "DATA"
                and tx.packet.flow_id == 3
            )
            observed[name] = (
                tuple((packet.path, packet.repair_index,
                       packet.backup_relay_id, packet.backup_epoch_id,
                       packet.wire_size_bytes(32))
                      for packet in (first_ack, direct_r, backup_r, backup_ack)),
                next_r,
            )

        self.assertEqual(observed["meshecho-dcb"][0],
                         observed["meshecho-dcb-promote"][0])
        self.assertEqual(observed["meshecho-dcb"][0][0][2], 2)
        self.assertEqual(observed["meshecho-dcb"][0][1][0], (0, 3))
        self.assertEqual(observed["meshecho-dcb"][0][2][0], (0, 2, 3))
        self.assertEqual(observed["meshecho-dcb"][0][3][0], (0, 2, 3))
        self.assertEqual(observed["meshecho-dcb"][1].path, (0, 3))
        promoted = observed["meshecho-dcb-promote"][1]
        self.assertEqual(promoted.path, (0, 2, 3))
        self.assertIsNone(promoted.backup_relay_id)
        self.assertIsNone(promoted.backup_epoch_id)

    def test_backup_ack_stages_one_two_hop_trial_without_route_commit(self):
        protocol = build_protocol("meshecho-dcb-trial")
        protocol.flood_base_delay_s = 0.5
        protocol.flood_jitter_s = 0.0
        sim = DropPrimarySimulator(
            [Node(i, i * 10.0, 0.0) for i in range(4)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        for flow_id, when in enumerate((1.0, 5.0, 10.0), start=1):
            sim.schedule(when, "app_send", (0, 3, flow_id))

        metrics = sim.run(10.05)

        self.assertIsNotNone(metrics.flows[2].acked_at)
        self.assertEqual(protocol.route_cache[0][3].path, (0, 3))
        trial = next(
            tx.packet for tx in sim.tx_history
            if tx.sender == 0 and tx.packet.kind == "DATA"
            and tx.packet.flow_id == 3
        )
        self.assertEqual(trial.path, (0, 2, 3))
        self.assertFalse(any(
            event.get("event") == "commit" and event["flow_id"] == 2
            for event in protocol.action_events
        ))

    def test_trial_route_commits_only_after_its_ordinary_ack(self):
        protocol = build_protocol("meshecho-dcb-trial")
        protocol.flood_base_delay_s = 0.5
        protocol.flood_jitter_s = 0.0
        sim = DropPrimarySimulator(
            [Node(i, i * 10.0, 0.0) for i in range(4)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        for flow_id, when in enumerate((1.0, 5.0, 10.0), start=1):
            sim.schedule(when, "app_send", (0, 3, flow_id))

        sim.run(10.05)
        self.assertEqual(protocol.route_cache[0][3].path, (0, 3))
        metrics = sim.run(13.0)

        self.assertIsNotNone(metrics.flows[3].acked_at)
        self.assertEqual(protocol.route_cache[0][3].path, (0, 2, 3))
        self.assertTrue(any(
            event.get("event") == "commit" and event["flow_id"] == 3
            and event["path"] == (0, 2, 3)
            for event in protocol.action_events
        ))

    def test_trial_source_keeps_acked_route_instead_of_age_discovery(self):
        observed = {}
        for name in ("meshecho-dcb", "meshecho-dcb-trial"):
            protocol = build_protocol(name)
            protocol.flood_base_delay_s = 0.5
            protocol.flood_jitter_s = 0.0
            sim = TraceSimulator(
                [Node(i, i * 10.0, 0.0) for i in range(4)],
                RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
                seed=17, max_hops=6, independent_random_streams=True,
            )
            for flow_id, when in enumerate((1.0, 20.0, 200.0), start=1):
                sim.schedule(when, "app_send", (0, 3, flow_id))
            sim.run(205.0)
            observed[name] = [
                event["action"] for event in protocol.action_events
                if event["event"] == "decision"
            ]

        self.assertEqual(observed["meshecho-dcb"], ["F", "R", "D"])
        self.assertEqual(observed["meshecho-dcb-trial"], ["F", "R", "R"])

    def test_late_trial_ack_after_guard_cannot_commit_abandoned_path(self):
        protocol = build_protocol("meshecho-dcb-trial")
        protocol.flood_base_delay_s = 0.5
        protocol.flood_jitter_s = 0.0
        sim = DropTrialRecoverySimulator(
            [Node(i, i * 10.0, 0.0) for i in range(4)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        for flow_id, when in enumerate((1.0, 5.0, 10.0), start=1):
            sim.schedule(when, "app_send", (0, 3, flow_id))
        sim.schedule(10.22, "protocol_timer",
                     lambda: setattr(sim.nodes[2], "tx_available_at", 27.0))

        metrics = sim.run(29.0)

        self.assertGreater(metrics.flows[3].acked_at, 25.0)
        self.assertEqual(protocol.route_cache[0][3].path, (0, 3))
        self.assertFalse(any(
            event.get("event") == "commit" and event["flow_id"] == 3
            and event["action"] == "R-trial"
            for event in protocol.action_events
        ))

    def test_trial_source_uses_f_after_one_unresolved_route_ack_miss(self):
        observed = {}
        for name in ("meshecho-dcb", "meshecho-dcb-trial"):
            protocol = build_protocol(name)
            protocol.flood_base_delay_s = 0.5
            protocol.flood_jitter_s = 0.0
            sim = DropSecondFlowDeliverySimulator(
                [Node(i, i * 10.0, 0.0) for i in range(4)],
                RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
                seed=17, max_hops=6, independent_random_streams=True,
            )
            for flow_id, when in enumerate((1.0, 5.0, 22.0), start=1):
                sim.schedule(when, "app_send", (0, 3, flow_id))
            sim.run(24.0)
            observed[name] = [
                event["action"] for event in protocol.action_events
                if event["event"] == "decision"
            ]

        self.assertEqual(observed["meshecho-dcb"], ["F", "R", "R"])
        self.assertEqual(observed["meshecho-dcb-trial"], ["F", "R", "F"])

    def test_no_switch_control_has_identical_pretrial_wire(self):
        observed = {}
        for name in ("meshecho-dcb-trial", "meshecho-dcb-trial-no-switch"):
            protocol = build_protocol(name)
            protocol.flood_base_delay_s = 0.5
            protocol.flood_jitter_s = 0.0
            sim = DropPrimarySimulator(
                [Node(i, i * 10.0, 0.0) for i in range(4)],
                RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
                seed=17, max_hops=6, independent_random_streams=True,
            )
            for flow_id, when in enumerate((1.0, 5.0, 10.0), start=1):
                sim.schedule(when, "app_send", (0, 3, flow_id))
            sim.run(10.05)
            packets = [
                tx.packet for tx in sim.tx_history
                if (tx.packet.flow_id == 1 and tx.sender == 3
                    and tx.packet.kind == "ACK")
                or (tx.packet.flow_id == 2 and (
                    (tx.sender == 0 and tx.packet.kind == "DATA")
                    or (tx.sender == 2 and tx.packet.kind == "DATA"
                        and tx.packet.repair_index == 4)
                    or (tx.sender == 3 and tx.packet.kind == "ACK"
                        and tx.packet.repair_index == 4)))
            ]
            observed[name] = (
                [(packet.kind, packet.path, packet.repair_index,
                  packet.backup_relay_id, packet.backup_epoch_id,
                  packet.wire_size_bytes(32)) for packet in packets],
                next(tx.packet.path for tx in sim.tx_history
                     if tx.sender == 0 and tx.packet.kind == "DATA"
                     and tx.packet.flow_id == 3),
            )

        self.assertEqual(observed["meshecho-dcb-trial"][0],
                         observed["meshecho-dcb-trial-no-switch"][0])
        self.assertEqual(observed["meshecho-dcb-trial"][1], (0, 2, 3))
        self.assertEqual(observed["meshecho-dcb-trial-no-switch"][1], (0, 3))

    def test_blind_switch_control_keeps_source_rule_and_wire_budget(self):
        observed = {}
        for name in ("meshecho-dcb-trial", "meshecho-dcb-trial-blind"):
            protocol = build_protocol(name)
            protocol.flood_base_delay_s = 0.5
            protocol.flood_jitter_s = 0.0
            sim = DropPrimarySimulator(
                [Node(i, i * 10.0, 0.0) for i in range(4)],
                RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
                seed=17, max_hops=6, independent_random_streams=True,
            )
            for flow_id, when in enumerate((1.0, 5.0, 10.0), start=1):
                sim.schedule(when, "app_send", (0, 3, flow_id))
            sim.run(9.0)
            route_before_next = protocol.route_cache[0][3].path
            signatures = [
                (tx.sender, tx.packet.kind, tx.packet.path,
                 tx.packet.repair_index, tx.packet.wire_size_bytes(32))
                for tx in sim.tx_history if tx.packet.flow_id <= 2
            ]
            sim.run(10.05)
            next_path = next(
                tx.packet.path for tx in sim.tx_history
                if tx.sender == 0 and tx.packet.kind == "DATA"
                and tx.packet.flow_id == 3
            )
            observed[name] = (signatures, route_before_next, next_path)

        self.assertEqual(observed["meshecho-dcb-trial"][0],
                         observed["meshecho-dcb-trial-blind"][0])
        self.assertEqual(observed["meshecho-dcb-trial"][1], (0, 3))
        self.assertEqual(observed["meshecho-dcb-trial-blind"][1], (0, 2, 3))
        self.assertEqual(observed["meshecho-dcb-trial"][2], (0, 2, 3))
        self.assertEqual(observed["meshecho-dcb-trial-blind"][2], (0, 2, 3))

    def test_older_backup_ack_replay_cannot_replace_newer_pending_trial(self):
        protocol = build_protocol("meshecho-dcb-trial")
        protocol.flood_base_delay_s = 0.5
        protocol.flood_jitter_s = 0.0
        sim = DropOlderBackupAckSimulator(
            [Node(i, i * 10.0, 0.0) for i in range(4)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        for flow_id, when in enumerate((1.0, 5.0, 8.0), start=1):
            sim.schedule(when, "app_send", (0, 3, flow_id))

        def replay_old_ack():
            packet = next(
                tx.packet for tx in sim.tx_history
                if tx.sender == 2 and tx.packet.kind == "ACK"
                and tx.packet.flow_id == 2 and tx.packet.repair_index == 4
            )
            sim.transmit_later(2, packet, delay_s=0.0)

        sim.schedule(12.0, "protocol_timer", replay_old_ack)
        metrics = sim.run(13.0)

        self.assertTrue(sim.dropped_old_ack)
        self.assertLess(metrics.flows[3].acked_at, metrics.flows[2].acked_at)
        self.assertEqual([
            event["flow_id"] for event in protocol.action_events
            if event["event"] == "trial_pending"
        ], [3])

    def test_active_trial_prevents_a_second_concurrent_trial(self):
        protocol = build_protocol("meshecho-dcb-trial")
        protocol.flood_base_delay_s = 0.5
        protocol.flood_jitter_s = 0.0
        sim = DropTrialAndFourthPrimarySimulator(
            [Node(i, i * 10.0, 0.0) for i in range(4)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        for flow_id, when in enumerate((1.0, 5.0, 10.0, 11.0, 15.0), start=1):
            sim.schedule(when, "app_send", (0, 3, flow_id))

        metrics = sim.run(15.05)

        self.assertIsNotNone(metrics.flows[4].acked_at)
        next_data = next(
            tx.packet for tx in sim.tx_history
            if tx.sender == 0 and tx.packet.kind == "DATA"
            and tx.packet.flow_id == 5
        )
        self.assertEqual(next_data.path, (0, 3))
        self.assertEqual([
            event["flow_id"] for event in protocol.action_events
            if event["event"] == "decision"
            and event["reason"] == "ack-proven-trial"
        ], [3])

    def test_older_unresolved_r_miss_survives_newer_direct_ack(self):
        protocol = build_protocol("meshecho-dcb-trial")
        protocol.flood_base_delay_s = 0.5
        protocol.flood_jitter_s = 0.0
        sim = DropSecondFlowDeliverySimulator(
            [Node(i, i * 10.0, 0.0) for i in range(4)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        for flow_id, when in enumerate((1.0, 5.0, 6.0, 22.0), start=1):
            sim.schedule(when, "app_send", (0, 3, flow_id))

        metrics = sim.run(23.0)

        self.assertIsNone(metrics.flows[2].acked_at)
        self.assertIsNotNone(metrics.flows[3].acked_at)
        decision = next(
            event for event in protocol.action_events
            if event["event"] == "decision" and event["flow_id"] == 4
        )
        self.assertEqual(decision["action"], "F")
        self.assertEqual(decision["reason"], "route-ack-miss")

    def test_old_route_timeout_does_not_taint_new_f_committed_route(self):
        protocol = build_protocol("meshecho-dcb-trial")
        protocol.flood_base_delay_s = 0.5
        protocol.flood_jitter_s = 0.0
        sim = DropMiddleFlowsDeliverySimulator(
            [Node(i, i * 10.0, 0.0) for i in range(4)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        for flow_id, when in enumerate((1.0, 5.0, 14.0, 21.0, 30.0), start=1):
            sim.schedule(when, "app_send", (0, 3, flow_id))

        metrics = sim.run(31.0)

        self.assertIsNotNone(metrics.flows[4].acked_at)
        decisions = {
            event["flow_id"]: event for event in protocol.action_events
            if event["event"] == "decision"
        }
        self.assertEqual(decisions[4]["action"], "F")
        self.assertEqual(decisions[5]["action"], "R")
        self.assertEqual(decisions[5]["reason"], "confirmed-route")

    def test_new_f_commit_invalidates_active_old_trial(self):
        protocol = build_protocol("meshecho-dcb-trial")
        protocol.flood_base_delay_s = 0.5
        protocol.flood_jitter_s = 0.0
        sim = DropStaleTrialAndNewPrimarySimulator(
            [Node(i, i * 10.0, 0.0) for i in range(4)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        for flow_id, when in enumerate(
            (1.0, 4.0, 7.0, 10.0, 20.0, 22.3, 24.9), start=1
        ):
            sim.schedule(when, "app_send", (0, 3, flow_id))

        metrics = sim.run(22.2)

        self.assertIsNotNone(metrics.flows[5].acked_at)
        self.assertIsNone(protocol.destination_state[(0, 3)].active_trial_flow)
        sim.run(25.0)
        self.assertTrue(any(
            event["event"] == "trial_pending" and event["flow_id"] == 6
            for event in protocol.action_events
        ))
        next_data = next(
            tx.packet for tx in sim.tx_history
            if tx.sender == 0 and tx.packet.kind == "DATA"
            and tx.packet.flow_id == 7
        )
        self.assertEqual(next_data.path, (0, 2, 3))

    def test_pending_trial_is_discarded_when_confirmed_route_expires(self):
        protocol = build_protocol(
            "meshecho-dcb-trial", SimpleNamespace(calm_route_ttl_s=8.0)
        )
        protocol.flood_base_delay_s = 0.5
        protocol.flood_jitter_s = 0.0
        sim = DropPrimarySimulator(
            [Node(i, i * 10.0, 0.0) for i in range(4)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        for flow_id, when in enumerate((1.0, 5.0, 12.0), start=1):
            sim.schedule(when, "app_send", (0, 3, flow_id))

        sim.run(9.0)
        self.assertEqual(protocol.destination_state[(0, 3)].trial_path, (0, 2, 3))
        sim.run(12.1)
        decision = next(
            event for event in protocol.action_events
            if event["event"] == "decision" and event["flow_id"] == 3
        )
        self.assertEqual(decision["action"], "F")
        self.assertEqual(decision["reason"], "no-confirmed-route")
        self.assertEqual(protocol.destination_state[(0, 3)].trial_path, ())

    def test_pending_trial_is_discarded_after_source_state_eviction(self):
        protocol = build_protocol("meshecho-dcb-trial")
        protocol.flood_base_delay_s = 0.5
        protocol.flood_jitter_s = 0.0
        sim = DropPrimarySimulator(
            [Node(i, i * 10.0, 0.0) for i in range(4)]
            + [Node(i, 1_000_000.0 + i * 10.0, 0.0)
               for i in range(4, 12)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 3, 1))
        sim.schedule(5.0, "app_send", (0, 3, 2))
        for flow_id, dst in enumerate(range(4, 12), start=3):
            sim.schedule(8.0 + (flow_id - 3) * 0.1,
                         "app_send", (0, dst, flow_id))
        sim.schedule(9.0, "app_send", (0, 3, 11))

        sim.run(7.9)
        old_state = protocol.destination_state[(0, 3)]
        self.assertEqual(old_state.trial_path, (0, 2, 3))
        sim.run(9.1)
        decision = next(
            event for event in protocol.action_events
            if event["event"] == "decision" and event["flow_id"] == 11
        )
        self.assertNotIn((0, 3), protocol.route_cache[0])
        self.assertIsNot(protocol.destination_state[(0, 3)], old_state)
        self.assertEqual(decision["action"], "F")
        self.assertEqual(decision["reason"], "no-confirmed-route")

    def test_newer_queued_direct_ack_supersedes_older_trial_commit(self):
        protocol = build_protocol("meshecho-dcb-trial")
        protocol.flood_base_delay_s = 0.5
        protocol.flood_jitter_s = 0.0
        sim = DropPrimarySimulator(
            [Node(i, i * 10.0, 0.0) for i in range(4)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        for flow_id, when in enumerate((1.0, 5.0, 10.0), start=1):
            sim.schedule(when, "app_send", (0, 3, flow_id))
        sim.schedule(10.20, "protocol_timer",
                     lambda: setattr(sim.nodes[0], "tx_available_at", 10.4))
        sim.schedule(10.25, "app_send", (0, 3, 4))

        metrics = sim.run(12.0)

        self.assertLess(metrics.flows[3].acked_at, metrics.flows[4].acked_at)
        queued_direct = next(
            tx.packet for tx in sim.tx_history
            if tx.sender == 0 and tx.packet.kind == "DATA"
            and tx.packet.flow_id == 4
        )
        self.assertEqual(queued_direct.path, (0, 3))
        self.assertEqual(protocol.route_cache[0][3].path, (0, 3))

    def test_old_backup_ack_cannot_replace_a_newer_confirmed_route(self):
        protocol = build_protocol(
            "meshecho-dcb-promote", SimpleNamespace(calm_route_ttl_s=4.0)
        )
        protocol.flood_base_delay_s = 0.5
        protocol.flood_jitter_s = 0.0
        sim = DropPrimarySimulator(
            [Node(i, i * 10.0, 0.0) for i in range(4)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 3, 1))
        sim.schedule(5.0, "app_send", (0, 3, 2))
        sim.schedule(7.23, "protocol_timer",
                     lambda: setattr(sim.nodes[2], "tx_available_at", 11.0))
        sim.schedule(8.0, "app_send", (0, 3, 3))
        sim.schedule(12.0, "app_send", (0, 3, 4))

        metrics = sim.run(14.0)

        self.assertEqual(protocol.flow_data_actions[3], "F")
        self.assertLess(metrics.flows[3].acked_at, metrics.flows[2].acked_at)
        self.assertLess(metrics.flows[2].acked_at, 35.0)
        self.assertTrue(any(
            event.get("event") == "dcb_source_ack_rx"
            and event["flow_id"] == 2 and event["accepted"]
            for event in protocol.action_events
        ))
        next_r = next(
            tx.packet for tx in sim.tx_history
            if tx.sender == 0 and tx.packet.kind == "DATA"
            and tx.packet.flow_id == 4
        )
        self.assertEqual(next_r.path, (0, 3))
        self.assertFalse(any(
            event.get("event") == "commit" and event["flow_id"] == 2
            for event in protocol.action_events
        ))

    def test_old_backup_ack_cannot_replace_newer_direct_ack_evidence(self):
        protocol = build_protocol("meshecho-dcb-promote")
        protocol.flood_base_delay_s = 0.5
        protocol.flood_jitter_s = 0.0
        sim = DropPrimarySimulator(
            [Node(i, i * 10.0, 0.0) for i in range(4)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        for flow_id, when in enumerate((1.0, 5.0, 6.0, 11.0), start=1):
            sim.schedule(when, "app_send", (0, 3, flow_id))

        metrics = sim.run(14.0)

        self.assertLess(metrics.flows[3].acked_at, metrics.flows[2].acked_at)
        self.assertTrue(any(
            event.get("event") == "dcb_source_ack_rx"
            and event["flow_id"] == 2 and event["accepted"]
            for event in protocol.action_events
        ))
        next_r = next(
            tx.packet for tx in sim.tx_history
            if tx.sender == 0 and tx.packet.kind == "DATA"
            and tx.packet.flow_id == 4
        )
        self.assertEqual(next_r.path, (0, 3))
        self.assertFalse(any(
            event.get("event") == "commit" and event["flow_id"] == 2
            for event in protocol.action_events
        ))

    def test_late_backup_ack_cannot_promote_the_candidate_route(self):
        protocol = build_protocol("meshecho-dcb-promote")
        protocol.flood_base_delay_s = 0.5
        protocol.flood_jitter_s = 0.0
        sim = DropSecondFlowDeliverySimulator(
            [Node(i, i * 10.0, 0.0) for i in range(4)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 3, 1))
        sim.schedule(5.0, "app_send", (0, 3, 2))
        late_ack = Packet(
            kind="ACK", flow_id=2, origin=3, final_dst=0, ttl=6,
            created_at=5.0, protocol=protocol.name, request_id=2,
            path=(0, 2, 3), path_index=0, app_payload=False,
            repair_index=4, backup_epoch_id=1,
        )
        sim.schedule(36.0, "protocol_timer",
                     lambda: sim.transmit_later(2, late_ack, 0.0))
        sim.schedule(37.0, "app_send", (0, 3, 3))

        metrics = sim.run(39.0)

        self.assertIsNone(metrics.flows[2].acked_at)
        next_r = next(
            tx.packet for tx in sim.tx_history
            if tx.sender == 0 and tx.packet.kind == "DATA"
            and tx.packet.flow_id == 3
        )
        self.assertEqual(next_r.path, (0, 3))
        self.assertFalse(any(
            event.get("event") == "commit" and event["flow_id"] == 2
            for event in protocol.action_events
        ))

    def test_overheard_direct_ack_cancels_the_nominated_relay(self):
        protocol = build_protocol("meshecho-dcb")
        protocol.flood_base_delay_s = 0.5
        protocol.flood_jitter_s = 0.0
        sim = TraceSimulator(
            [Node(i, i * 10.0, 0.0) for i in range(4)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 3, 1))
        sim.schedule(5.0, "app_send", (0, 3, 2))

        metrics = sim.run(10.0)

        self.assertIsNotNone(metrics.flows[2].acked_at)
        self.assertFalse(any(
            tx.sender == 2 and tx.packet.flow_id == 2
            and tx.packet.repair_index == 4
            for tx in sim.tx_history
        ))

    def test_wrong_epoch_backup_ack_cannot_confirm_the_current_flow(self):
        protocol = build_protocol("meshecho-dcb")
        protocol.flood_base_delay_s = 0.5
        protocol.flood_jitter_s = 0.0
        sim = DropPrimarySimulator(
            [Node(i, i * 10.0, 0.0) for i in range(4)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 3, 1))
        sim.schedule(5.0, "app_send", (0, 3, 2))
        forged = Packet(
            kind="ACK", flow_id=2, origin=3, final_dst=0, ttl=6,
            created_at=5.0, protocol="meshecho-dcb", request_id=2,
            path=(0, 2, 3), path_index=1, app_payload=False,
            repair_index=4, backup_epoch_id=999,
        )
        sim.schedule(5.5, "protocol_timer",
                     lambda: sim.transmit_later(3, forged, 0.0))

        metrics = sim.run(6.5)

        self.assertIsNone(metrics.flows[2].acked_at)
        self.assertFalse(any(
            event.get("event") == "dcb_source_ack_rx" and event["accepted"]
            for event in protocol.action_events
        ))
        self.assertTrue(any(
            event.get("event") == "dcb_source_ack_rx"
            and event.get("reason") == "epoch-mismatch"
            for event in protocol.action_events
        ))

    def test_wrong_physical_ack_sender_is_rejected_with_a_reason(self):
        protocol = build_protocol("meshecho-dcb")
        protocol.flood_base_delay_s = 0.5
        protocol.flood_jitter_s = 0.0
        sim = DropPrimarySimulator(
            [Node(i, i * 10.0, 0.0) for i in range(4)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 3, 1))
        sim.schedule(5.0, "app_send", (0, 3, 2))
        forged = Packet(
            kind="ACK", flow_id=2, origin=3, final_dst=0, ttl=6,
            created_at=5.0, protocol="meshecho-dcb", request_id=2,
            path=(0, 2, 3), path_index=0, app_payload=False,
            repair_index=4, backup_epoch_id=1,
        )
        sim.schedule(5.5, "protocol_timer",
                     lambda: sim.transmit_later(1, forged, 0.0))

        metrics = sim.run(6.5)

        self.assertIsNone(metrics.flows[2].acked_at)
        self.assertTrue(any(
            event.get("event") == "dcb_source_ack_rx"
            and event.get("flow_id") == 2
            and event.get("reason") == "path-or-sender-mismatch"
            and not event.get("accepted")
            for event in protocol.action_events
        ))

    def test_late_backup_ack_cannot_confirm_after_the_original_deadline(self):
        protocol = build_protocol("meshecho-dcb")
        protocol.flood_base_delay_s = 0.5
        protocol.flood_jitter_s = 0.0
        sim = DropSecondFlowDeliverySimulator(
            [Node(i, i * 10.0, 0.0) for i in range(4)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 3, 1))
        sim.schedule(5.0, "app_send", (0, 3, 2))
        late_ack = Packet(
            kind="ACK", flow_id=2, origin=3, final_dst=0, ttl=6,
            created_at=5.0, protocol="meshecho-dcb", request_id=2,
            path=(0, 2, 3), path_index=0, app_payload=False,
            repair_index=4, backup_epoch_id=1,
        )
        sim.schedule(36.0, "protocol_timer",
                     lambda: sim.transmit_later(2, late_ack, 0.0))

        metrics = sim.run(37.0)

        self.assertIsNone(metrics.flows[2].acked_at)
        self.assertTrue(any(
            event.get("event") == "dcb_source_ack_rx"
            and event.get("flow_id") == 2
            and event.get("reason") in {"inactive-flow", "deadline-expired"}
            and not event.get("accepted")
            for event in protocol.action_events
        ))

    def test_nominated_r_activates_only_at_its_physical_radio_start(self):
        protocol = build_protocol("meshecho-dcb")
        protocol.flood_base_delay_s = 0.5
        protocol.flood_jitter_s = 0.0
        sim = TraceSimulator(
            [Node(i, i * 10.0, 0.0) for i in range(4)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 3, 1))
        sim.schedule(4.9, "protocol_timer",
                     lambda: setattr(sim.nodes[0], "tx_available_at", 6.0))
        sim.schedule(5.0, "app_send", (0, 3, 2))

        sim.run(5.5)
        self.assertNotIn(2, protocol.active_nominations)
        self.assertNotIn(2, protocol.active_flows)

        sim.run(6.0)
        self.assertIn(2, protocol.active_nominations)
        self.assertIn(2, protocol.active_flows)
        self.assertAlmostEqual(protocol.active_nominations[2].start, 6.0)
        self.assertAlmostEqual(protocol.active_flows[2].initial_start, 6.0)

    def test_r_start_after_application_deadline_does_not_activate_recovery(self):
        protocol = build_protocol("meshecho-dcb")
        protocol.flood_base_delay_s = 0.5
        protocol.flood_jitter_s = 0.0
        sim = NoPastEventSimulator(
            [Node(i, i * 10.0, 0.0) for i in range(4)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 3, 1))
        sim.schedule(4.9, "protocol_timer",
                     lambda: setattr(sim.nodes[0], "tx_available_at", 36.0))
        sim.schedule(5.0, "app_send", (0, 3, 2))

        sim.run(37.0)

        self.assertNotIn(2, protocol.active_flows)
        self.assertNotIn(2, protocol.active_nominations)

    def test_no_forward_control_keeps_fields_and_fixed_f_recovery(self):
        protocol = build_protocol("meshecho-dcb-no-forward")
        protocol.flood_base_delay_s = 0.5
        protocol.flood_jitter_s = 0.0
        sim = DropPrimarySimulator(
            [Node(i, i * 10.0, 0.0) for i in range(4)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 3, 1))
        sim.schedule(5.0, "app_send", (0, 3, 2))

        sim.run(22.0)

        initial = next(tx for tx in sim.tx_history
                       if tx.sender == 0 and tx.packet.flow_id == 2
                       and tx.packet.kind == "DATA")
        self.assertEqual(initial.packet.backup_relay_id, 2)
        self.assertEqual(initial.packet.backup_epoch_id, 1)
        self.assertFalse(any(
            tx.packet.flow_id == 2 and tx.packet.repair_index == 4
            for tx in sim.tx_history
        ))
        recoveries = [tx for tx in sim.tx_history
                      if tx.sender == 0 and tx.packet.flow_id == 2
                      and tx.packet.kind == "FLOOD"
                      and tx.packet.repair_index == 2]
        self.assertEqual(len(recoveries), 1)
        self.assertAlmostEqual(recoveries[0].start - initial.start, 15.0)

    def test_unconditional_control_sends_despite_overheard_primary_ack(self):
        protocol = build_protocol("meshecho-dcb-unconditional")
        protocol.flood_base_delay_s = 0.5
        protocol.flood_jitter_s = 0.0
        sim = TraceSimulator(
            [Node(i, i * 10.0, 0.0) for i in range(4)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 3, 1))
        sim.schedule(5.0, "app_send", (0, 3, 2))

        metrics = sim.run(10.0)

        self.assertIsNotNone(metrics.flows[2].acked_at)
        self.assertEqual(len([
            tx for tx in sim.tx_history
            if tx.sender == 2 and tx.packet.flow_id == 2
            and tx.packet.kind == "DATA"
            and tx.packet.repair_index == 4
        ]), 1)

    def test_current_overhear_control_can_use_a_non_nominated_relay(self):
        protocol = build_protocol("meshecho-dcb-current-overhear")
        protocol.flood_base_delay_s = 0.5
        protocol.flood_jitter_s = 0.0
        sim = DropNominatedCurrentDataSimulator(
            [Node(i, i * 10.0, 0.0) for i in range(4)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 3, 1))
        sim.schedule(5.0, "app_send", (0, 3, 2))

        metrics = sim.run(10.0)

        initial = next(tx.packet for tx in sim.tx_history
                       if tx.sender == 0 and tx.packet.flow_id == 2
                       and tx.packet.kind == "DATA")
        self.assertEqual(initial.backup_relay_id, 2)
        backups = [tx for tx in sim.tx_history
                   if tx.packet.flow_id == 2 and tx.packet.kind == "DATA"
                   and tx.packet.repair_index == 4]
        self.assertTrue(any(tx.sender == 1 for tx in backups))
        self.assertFalse(any(tx.sender == 2 for tx in backups))
        self.assertIsNotNone(metrics.flows[2].acked_at)

    def test_malformed_flood_path_index_cannot_create_a_certified_ack(self):
        protocol = build_protocol("meshecho-dcb")
        sim = TraceSimulator(
            [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.metrics.register_flow(1, 0, 1, 0.0)
        malformed = Packet(
            kind="FLOOD", flow_id=1, origin=0, final_dst=1, ttl=6,
            created_at=0.0, protocol="meshecho-dcb", request_id=1,
            path=(0,), path_index=99,
        )
        sim.transmit_later(0, malformed, 0.0)

        metrics = sim.run(3.0)

        self.assertIsNone(metrics.flows[1].delivered_at)
        self.assertFalse(any(tx.packet.kind == "ACK" for tx in sim.tx_history))

    def test_marked_backup_data_requires_a_distinct_relay(self):
        protocol = build_protocol("meshecho-dcb")
        sim = TraceSimulator(
            [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.metrics.register_flow(1, 0, 1, 0.0)
        malformed = Packet(
            kind="DATA", flow_id=1, origin=0, final_dst=1, ttl=6,
            created_at=0.0, protocol="meshecho-dcb", request_id=1,
            path=(0, 0, 1), path_index=1, repair_index=4,
            backup_epoch_id=99,
        )
        sim.transmit_later(0, malformed, 0.0)

        metrics = sim.run(3.0)

        self.assertIsNone(metrics.flows[1].delivered_at)
        self.assertFalse(any(tx.packet.kind == "ACK" for tx in sim.tx_history))

    def test_marked_backup_data_requires_matching_flow_identity(self):
        protocol = build_protocol("meshecho-dcb")
        sim = TraceSimulator(
            [Node(i, i * 10.0, 0.0) for i in range(3)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.metrics.register_flow(1, 0, 2, 0.0)
        malformed = Packet(
            kind="DATA", flow_id=1, origin=0, final_dst=2, ttl=6,
            created_at=0.0, protocol="meshecho-dcb", request_id=99,
            path=(0, 1, 2), path_index=1, repair_index=4,
            backup_epoch_id=7,
        )
        sim.transmit_later(1, malformed, 0.0)

        metrics = sim.run(3.0)

        self.assertIsNone(metrics.flows[1].delivered_at)
        self.assertFalse(any(tx.packet.kind == "ACK" for tx in sim.tx_history))

    def test_malformed_backup_overhear_cannot_suppress_a_valid_contender(self):
        protocol = build_protocol("meshecho-dcb-current-overhear")
        protocol.flood_base_delay_s = 0.5
        protocol.flood_jitter_s = 0.0
        sim = DropNominatedCurrentDataSimulator(
            [Node(i, i * 10.0, 0.0) for i in range(4)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 3, 1))
        sim.schedule(5.0, "app_send", (0, 3, 2))
        malformed = Packet(
            kind="DATA", flow_id=2, origin=0, final_dst=3, ttl=6,
            created_at=5.0, protocol="meshecho-dcb-current-overhear",
            request_id=99, path=(0, 0, 3), path_index=1,
            repair_index=4, backup_epoch_id=1,
        )
        sim.schedule(5.12, "protocol_timer",
                     lambda: sim.transmit_later(0, malformed, 0.0))

        sim.run(10.0)

        self.assertTrue(any(
            tx.sender == 1 and tx.packet.kind == "DATA"
            and tx.packet.flow_id == 2 and tx.packet.repair_index == 4
            for tx in sim.tx_history
        ))

    def test_duplicate_current_data_cannot_trigger_a_second_backup(self):
        protocol = build_protocol("meshecho-dcb")
        protocol.flood_base_delay_s = 0.5
        protocol.flood_jitter_s = 0.0
        sim = DropPrimarySimulator(
            [Node(i, i * 10.0, 0.0) for i in range(4)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 3, 1))
        sim.schedule(5.0, "app_send", (0, 3, 2))
        duplicate = Packet(
            kind="DATA", flow_id=2, origin=0, final_dst=3, ttl=6,
            created_at=5.0, protocol="meshecho-dcb", request_id=2,
            path=(0, 3), backup_relay_id=2, backup_epoch_id=1,
        )
        sim.schedule(10.0, "protocol_timer",
                     lambda: sim.transmit_later(0, duplicate, 0.0))

        sim.run(15.0)

        backups = [tx for tx in sim.tx_history
                   if tx.sender == 2 and tx.packet.kind == "DATA"
                   and tx.packet.flow_id == 2 and tx.packet.repair_index == 4]
        self.assertEqual(len(backups), 1)

    def test_busy_relay_skips_backup_without_delaying_the_fixed_f_guard(self):
        protocol = build_protocol("meshecho-dcb")
        protocol.flood_base_delay_s = 0.5
        protocol.flood_jitter_s = 0.0
        sim = DropPrimarySimulator(
            [Node(i, i * 10.0, 0.0) for i in range(4)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 3, 1))
        sim.schedule(5.0, "app_send", (0, 3, 2))
        sim.schedule(7.0, "protocol_timer",
                     lambda: setattr(sim.nodes[2], "tx_available_at", 8.0))

        sim.run(22.0)

        initial = next(tx for tx in sim.tx_history
                       if tx.sender == 0 and tx.packet.flow_id == 2
                       and tx.packet.kind == "DATA")
        self.assertFalse(any(
            tx.sender == 2 and tx.packet.kind == "DATA"
            and tx.packet.flow_id == 2 and tx.packet.repair_index == 4
            for tx in sim.tx_history
        ))
        floods = [tx for tx in sim.tx_history
                  if tx.sender == 0 and tx.packet.kind == "FLOOD"
                  and tx.packet.flow_id == 2 and tx.packet.repair_index == 2]
        self.assertEqual(len(floods), 1)
        self.assertAlmostEqual(floods[0].start - initial.start, 15.0)
        self.assertTrue(any(
            event.get("event") == "dcb_relay_skip"
            and event.get("reason") == "busy-radio"
            and event.get("flow_id") == 2
            for event in protocol.action_events
        ))

    def test_feedback_window_capacity_still_acks_the_ninth_flow_once(self):
        protocol = build_protocol("meshecho-dcb")
        sim = TraceSimulator(
            [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        for flow_id in range(1, 10):
            sim.schedule(1.0 + 0.14 * (flow_id - 1),
                         "app_send", (0, 1, flow_id))

        sim.run(2.5)
        self.assertEqual(len(protocol.feedback_windows), 8)
        ninth_data = next(tx for tx in sim.tx_history
                          if tx.sender == 0 and tx.packet.flow_id == 9
                          and tx.packet.kind == "FLOOD")
        ninth_acks = [tx for tx in sim.tx_history
                      if tx.sender == 1 and tx.packet.flow_id == 9
                      and tx.packet.kind == "ACK"]
        self.assertEqual(len(ninth_acks), 1)
        self.assertAlmostEqual(ninth_acks[0].start, ninth_data.end)
        self.assertIsNone(ninth_acks[0].packet.backup_relay_id)

        sim.run(6.0)
        acks = [tx for tx in sim.tx_history
                if tx.sender == 1 and tx.packet.kind == "ACK"]
        self.assertEqual(len(acks), 9)
        self.assertEqual(len(protocol.feedback_windows), 0)

    def test_ack_rx_at_exact_relay_timer_suppresses_backup(self):
        protocol = build_protocol("meshecho-dcb")
        sim = DropPrimarySimulator(
            [Node(i, i * 10.0, 0.0) for i in range(4)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.metrics.register_flow(2, 0, 3, 0.0)
        data = Packet(
            kind="DATA", flow_id=2, origin=0, final_dst=3, ttl=6,
            created_at=0.0, protocol="meshecho-dcb", request_id=2,
            path=(0, 3), backup_relay_id=2, backup_epoch_id=1,
        )
        sim.transmit_later(0, data, 0.0)
        sim.run(0.2)
        initial = next(tx for tx in sim.tx_history
                       if tx.sender == 0 and tx.packet.kind == "DATA")
        timer_at = initial.end + 2.0
        direct_ack = Packet(
            kind="ACK", flow_id=2, origin=3, final_dst=0, ttl=6,
            created_at=0.0, protocol="meshecho-dcb", request_id=2,
            path=(0, 3), path_index=0, app_payload=False,
        )
        ack_start = timer_at - sim.radio.packet_toa_s(direct_ack)
        sim.transmit_later(3, direct_ack, ack_start - sim.now)

        sim.run(3.0)

        self.assertFalse(any(
            tx.sender == 2 and tx.packet.kind == "DATA"
            and tx.packet.repair_index == 4 for tx in sim.tx_history
        ))
        self.assertTrue(any(
            event.get("event") == "dcb_relay_skip"
            and event.get("reason") == "overheard-ack-or-backup"
            for event in protocol.action_events
        ))


if __name__ == "__main__":
    unittest.main()
