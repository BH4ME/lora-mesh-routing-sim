import unittest

from lora_mesh_sim import Node, Packet, RadioConfig, RoutingProtocol, Simulator, build_protocol


class TraceSimulator(Simulator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tx_history = []

    def begin_transmission(self, sender, packet, pending):
        prior = self.metrics.tx_count
        super().begin_transmission(sender, packet, pending)
        if self.metrics.tx_count > prior:
            self.tx_history.append(self.transmissions[-1])

    def try_receive(self, tx, receiver):
        allowed = {(0, 2), (0, 3), (2, 3), (3, 0), (3, 2), (2, 0)}
        if (tx.sender, receiver) not in allowed:
            return None
        if (tx.packet.flow_id == 2 and tx.packet.kind == "DATA"
                and tx.packet.repair_index is None
                and (tx.sender, receiver) == (0, 3)):
            return None
        return super().try_receive(tx, receiver)


class DropBackupSimulator(TraceSimulator):
    def try_receive(self, tx, receiver):
        if (tx.packet.flow_id == 2 and tx.packet.kind == "DATA"
                and tx.packet.repair_index == 3):
            return None
        return super().try_receive(tx, receiver)


class DeferredBackupAckSimulator(TraceSimulator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.release_backup_ack = False

    def try_receive(self, tx, receiver):
        if (receiver == 0 and tx.sender == 2
                and tx.packet.kind == "ACK"
                and tx.packet.flow_id == 2
                and tx.packet.repair_index == 3
                and not self.release_backup_ack):
            return None
        return super().try_receive(tx, receiver)


class SimulatorDeliveryIdentityTest(unittest.TestCase):
    def test_normal_data_and_flood_credit_only_the_registered_source(self):
        class DeliveryProbe(RoutingProtocol):
            name = "delivery-probe"

            def __init__(self):
                self.deliveries = []

            def on_receive(self, receiver, packet, rx):
                if receiver == packet.final_dst:
                    self.sim.mark_delivered(packet.flow_id, receiver, packet)

            def on_delivery(self, flow_id, receiver, now, packet):
                self.deliveries.append((flow_id, receiver, packet.kind))

        for kind in ("DATA", "FLOOD"):
            with self.subTest(kind=kind):
                protocol = DeliveryProbe()
                sim = Simulator(
                    [Node(i, i * 10.0, 0.0) for i in range(4)],
                    RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
                    seed=17, max_hops=6, independent_random_streams=True,
                )
                sim.metrics.register_flow(1, 0, 3, 0.0)
                wrong_source = Packet(
                    kind=kind, flow_id=1, origin=2, final_dst=3, ttl=6,
                    created_at=0.0, protocol=protocol.name, request_id=1,
                    path=(2, 3),
                )
                valid_source = Packet(
                    kind=kind, flow_id=1, origin=0, final_dst=3, ttl=6,
                    created_at=0.0, protocol=protocol.name, request_id=1,
                    path=(0, 3),
                )
                sim.schedule(1.0, "protocol_timer",
                             lambda: sim.transmit_later(2, wrong_source, 0.0))
                sim.schedule(3.0, "protocol_timer",
                             lambda: sim.transmit_later(0, valid_source, 0.0))

                sim.run(2.0)
                self.assertIsNone(sim.metrics.flows[1].delivered_at)
                self.assertEqual(sim.metrics.unicast_deliveries, 0)
                self.assertEqual(protocol.deliveries, [])

                sim.run(4.0)
                self.assertIsNotNone(sim.metrics.flows[1].delivered_at)
                self.assertEqual(sim.metrics.unicast_deliveries, 1)
                self.assertEqual(protocol.deliveries, [(1, 3, kind)])


class MeshEchoDBRTest(unittest.TestCase):
    def test_one_delayed_ack_carries_a_decoded_first_hop_diverse_backup(self):
        protocol = build_protocol("meshecho-dbr")
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
        self.assertEqual(acks[0].packet.alternate_path, (0, 2, 3))
        self.assertAlmostEqual(acks[0].start - metrics.flows[1].delivered_at,
                               2.0)
        self.assertEqual(acks[0].packet.wire_size_bytes(32), 23)
        self.assertIsNotNone(metrics.flows[1].acked_at)

    def test_backup_route_is_used_only_after_primary_timeout_and_ack_commits_it(self):
        protocol = build_protocol("meshecho-dbr")
        protocol.flood_base_delay_s = 0.5
        protocol.flood_jitter_s = 0.0
        sim = TraceSimulator(
            [Node(i, i * 10.0, 0.0) for i in range(4)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        for at, flow_id in ((1.0, 1), (5.0, 2), (25.0, 3)):
            sim.schedule(at, "app_send", (0, 3, flow_id))

        metrics = sim.run(56.0)

        initial_second = next(
            tx for tx in sim.tx_history
            if tx.sender == 0 and tx.packet.flow_id == 2
            and tx.packet.kind == "DATA" and tx.packet.repair_index is None
        )
        backup_second = next(
            tx for tx in sim.tx_history
            if tx.sender == 0 and tx.packet.flow_id == 2
            and tx.packet.kind == "DATA" and tx.packet.repair_index == 3
        )
        third = next(
            tx for tx in sim.tx_history
            if tx.sender == 0 and tx.packet.flow_id == 3
            and tx.packet.kind == "DATA" and tx.packet.repair_index is None
        )
        self.assertEqual(initial_second.packet.path, (0, 3))
        self.assertAlmostEqual(backup_second.start - initial_second.start, 15.0)
        self.assertEqual(backup_second.packet.path, (0, 2, 3))
        self.assertIsNotNone(metrics.flows[2].acked_at)
        self.assertEqual(third.packet.path, (0, 2, 3))
        accepted_backup_acks = [
            event for event in protocol.action_events
            if event.get("event") == "dbr_source_ack_rx"
            and event["flow_id"] == 2 and event["accepted"]
        ]
        self.assertEqual(len(accepted_backup_acks), 1)
        self.assertEqual(accepted_backup_acks[0]["path"], (0, 2, 3))
        self.assertFalse(any(
            tx.sender == 0 and tx.packet.flow_id == 2
            and tx.packet.kind == "FLOOD" and tx.packet.repair_index == 2
            for tx in sim.tx_history
        ))

    def test_backup_miss_still_uses_one_flood_within_the_original_deadline(self):
        protocol = build_protocol("meshecho-dbr")
        protocol.flood_base_delay_s = 0.5
        protocol.flood_jitter_s = 0.0
        sim = DropBackupSimulator(
            [Node(i, i * 10.0, 0.0) for i in range(4)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 3, 1))
        sim.schedule(5.0, "app_send", (0, 3, 2))

        metrics = sim.run(36.0)

        source_recoveries = [
            tx for tx in sim.tx_history
            if tx.sender == 0 and tx.packet.flow_id == 2
            and tx.packet.repair_index is not None
        ]
        self.assertEqual(
            [(tx.packet.kind, tx.packet.repair_index)
             for tx in source_recoveries],
            [("DATA", 3), ("FLOOD", 2)],
        )
        self.assertAlmostEqual(source_recoveries[1].start
                               - source_recoveries[0].start, 2.0)
        self.assertIsNotNone(metrics.flows[2].acked_at)
        self.assertLessEqual(metrics.flows[2].acked_at, 35.0)
        self.assertEqual(metrics.unicast_deliveries, 2)

    def test_busy_source_rechecks_flood_at_the_actual_idle_time(self):
        protocol = build_protocol("meshecho-dbr")
        protocol.flood_base_delay_s = 0.5
        protocol.flood_jitter_s = 0.0
        sim = DropBackupSimulator(
            [Node(i, i * 10.0, 0.0) for i in range(4)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 3, 1))
        sim.schedule(5.0, "app_send", (0, 3, 2))
        sim.schedule(
            21.9, "protocol_timer",
            lambda: setattr(sim.nodes[0], "tx_available_at", 24.0),
        )

        sim.run(36.0)

        floods = [tx for tx in sim.tx_history
                  if tx.sender == 0 and tx.packet.flow_id == 2
                  and tx.packet.kind == "FLOOD" and tx.packet.repair_index == 2]
        self.assertEqual(len(floods), 1)
        self.assertGreaterEqual(floods[0].start, 24.0)
        drops = [event for event in protocol.action_events
                 if event.get("event") == "dbr_recovery_request_drop"
                 and event["flow_id"] == 2 and event["action"] == "F"]
        self.assertEqual([event["reason"] for event in drops], ["source-queued"])

    def test_ack_from_a_node_not_adjacent_on_its_encoded_path_is_rejected(self):
        protocol = build_protocol("meshecho-dbr")
        protocol.flood_base_delay_s = 0.5
        protocol.flood_jitter_s = 0.0
        sim = TraceSimulator(
            [Node(i, i * 10.0, 0.0) for i in range(4)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 3, 1))
        forged = Packet(
            kind="ACK", flow_id=1, origin=3, final_dst=0, ttl=6,
            created_at=2.4, protocol=protocol.name, request_id=1,
            path=(0, 3), path_index=0, app_payload=False,
            alternate_path=(0, 2, 3),
        )
        sim.schedule(
            2.4, "protocol_timer",
            lambda: sim.transmit_later(2, forged, delay_s=0.0),
        )

        metrics = sim.run(2.9)

        self.assertIsNone(metrics.flows[1].acked_at)

    def test_padded_fixed_f_control_receives_backup_bytes_but_does_not_use_them(self):
        protocol = build_protocol("meshecho-dbr-fixed-f")
        protocol.flood_base_delay_s = 0.5
        protocol.flood_jitter_s = 0.0
        sim = TraceSimulator(
            [Node(i, i * 10.0, 0.0) for i in range(4)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 3, 1))
        sim.schedule(5.0, "app_send", (0, 3, 2))

        metrics = sim.run(36.0)

        first_ack = next(
            tx.packet for tx in sim.tx_history
            if tx.packet.kind == "ACK" and tx.packet.flow_id == 1
        )
        recoveries = [
            tx.packet for tx in sim.tx_history
            if tx.sender == 0 and tx.packet.flow_id == 2
            and tx.packet.repair_index is not None
        ]
        self.assertEqual(first_ack.alternate_path, (0, 2, 3))
        self.assertEqual(first_ack.wire_size_bytes(32), 23)
        self.assertEqual([(p.kind, p.repair_index) for p in recoveries],
                         [("FLOOD", 2)])
        self.assertIsNotNone(metrics.flows[2].acked_at)

    def test_same_path_control_probes_original_route_with_equal_feedback(self):
        protocol = build_protocol("meshecho-dbr-same")
        protocol.flood_base_delay_s = 0.5
        protocol.flood_jitter_s = 0.0
        sim = TraceSimulator(
            [Node(i, i * 10.0, 0.0) for i in range(4)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 3, 1))
        sim.schedule(5.0, "app_send", (0, 3, 2))

        metrics = sim.run(36.0)

        first_ack = next(tx.packet for tx in sim.tx_history
                         if tx.packet.kind == "ACK" and tx.packet.flow_id == 1)
        probes = [
            tx.packet for tx in sim.tx_history
            if tx.sender == 0 and tx.packet.flow_id == 2
            and tx.packet.kind == "DATA" and tx.packet.repair_index == 3
        ]
        self.assertEqual(first_ack.alternate_path, (0, 2, 3))
        self.assertEqual(len(probes), 1)
        self.assertEqual(probes[0].path, (0, 3))
        self.assertIsNotNone(metrics.flows[2].acked_at)

    def test_first_alternate_control_uses_an_old_backup_that_dbr_rejects(self):
        def run(name):
            protocol = build_protocol(name)
            protocol.flood_base_delay_s = 0.5
            protocol.flood_jitter_s = 0.0
            sim = TraceSimulator(
                [Node(i, i * 10.0, 0.0) for i in range(4)],
                RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
                seed=17, max_hops=6, independent_random_streams=True,
            )
            sim.schedule(1.0, "app_send", (0, 3, 1))
            sim.schedule(200.0, "app_send", (0, 3, 2))
            sim.run(231.0)
            return [
                (tx.packet.kind, tx.packet.repair_index, tx.packet.path)
                for tx in sim.tx_history
                if tx.sender == 0 and tx.packet.flow_id == 2
                and tx.packet.repair_index is not None
            ]

        self.assertEqual(run("meshecho-dbr")[0][:2], ("FLOOD", 2))
        self.assertEqual(run("meshecho-dbr-first-alt")[0],
                         ("DATA", 3, (0, 2, 3)))

    def test_plain_fixed_f_control_is_identical_except_ack_backup_bytes(self):
        def run(name):
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
            sim.run(36.0)
            ack = next(tx.packet for tx in sim.tx_history
                       if tx.packet.kind == "ACK" and tx.packet.flow_id == 1)
            actions = [(tx.packet.kind, tx.packet.repair_index)
                       for tx in sim.tx_history
                       if tx.sender == 0 and tx.packet.flow_id == 2
                       and tx.packet.repair_index is not None]
            return ack, actions

        padded_ack, padded_actions = run("meshecho-dbr-fixed-f")
        plain_ack, plain_actions = run("meshecho-dbr-fixed-f-plain")

        self.assertEqual(padded_actions, plain_actions)
        self.assertEqual(padded_actions, [("FLOOD", 2)])
        self.assertEqual(plain_ack.alternate_path, ())
        self.assertEqual(padded_ack.wire_size_bytes(32),
                         plain_ack.wire_size_bytes(32) + 7)

    def test_stale_backup_fallback_records_its_guard_reason(self):
        protocol = build_protocol("meshecho-dbr")
        protocol.flood_base_delay_s = 0.5
        protocol.flood_jitter_s = 0.0
        sim = TraceSimulator(
            [Node(i, i * 10.0, 0.0) for i in range(4)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 3, 1))
        sim.schedule(200.0, "app_send", (0, 3, 2))

        sim.run(231.0)

        guard = [event for event in protocol.action_events
                 if event.get("event") == "dbr_guard"
                 and event["flow_id"] == 2]
        self.assertEqual(len(guard), 1)
        self.assertEqual(guard[0]["selected_action"], "F")
        self.assertEqual(guard[0]["reason"], "backup-stale")
        self.assertTrue(any(
            tx.sender == 0 and tx.packet.flow_id == 2
            and tx.packet.kind == "FLOOD" and tx.packet.repair_index == 2
            for tx in sim.tx_history
        ))

    def test_backup_is_not_used_after_its_primary_route_expires(self):
        protocol = build_protocol("meshecho-dbr")
        protocol.route_ttl_s = 30.0
        protocol.flood_base_delay_s = 0.5
        protocol.flood_jitter_s = 0.0
        sim = TraceSimulator(
            [Node(i, i * 10.0, 0.0) for i in range(4)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 3, 1))
        sim.schedule(30.0, "app_send", (0, 3, 2))

        sim.run(61.0)

        recoveries = [tx.packet for tx in sim.tx_history
                      if tx.sender == 0 and tx.packet.flow_id == 2
                      and tx.packet.repair_index is not None]
        self.assertEqual([(p.kind, p.repair_index) for p in recoveries],
                         [("FLOOD", 2)])
        guard = next(event for event in protocol.action_events
                     if event.get("event") == "dbr_guard"
                     and event["flow_id"] == 2)
        self.assertEqual(guard["reason"], "primary-expired")

    def test_destination_acks_packet_claim_without_crediting_another_sources_flow(self):
        protocol = build_protocol("meshecho-dbr")
        sim = TraceSimulator(
            [Node(i, i * 10.0, 0.0) for i in range(4)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.metrics.register_flow(1, 0, 3, 0.0)
        forged = Packet(
            kind="FLOOD", flow_id=1, origin=2, final_dst=3, ttl=6,
            created_at=0.0, protocol=protocol.name, request_id=1,
            path=(2,),
        )
        sim.schedule(
            1.0, "protocol_timer",
            lambda: sim.transmit_later(2, forged, delay_s=0.0),
        )

        metrics = sim.run(5.0)

        self.assertIsNone(metrics.flows[1].delivered_at)
        replies = [tx.packet for tx in sim.tx_history
                   if tx.sender == 3 and tx.packet.kind == "ACK"]
        self.assertEqual(len(replies), 1)
        self.assertEqual((replies[0].final_dst, replies[0].path),
                         (2, (2, 3)))

    def test_flood_deadline_bound_includes_possible_backup_ack_bytes(self):
        protocol = build_protocol("meshecho-dbr")
        sim = Simulator(
            [Node(i, i * 10.0, 0.0) for i in range(7)],
            RadioConfig(sf=12, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        path = tuple(range(sim.max_hops + 1))
        flood = Packet(
            kind="FLOOD", flow_id=0, origin=0, final_dst=6, ttl=6,
            created_at=0.0, protocol=protocol.name, path=path,
            repair_index=2,
        )
        ack = Packet(
            kind="ACK", flow_id=0, origin=6, final_dst=0, ttl=6,
            created_at=0.0, protocol=protocol.name, path=path,
            app_payload=False, alternate_path=path, repair_index=2,
        )
        full_cost = sim.max_hops * (
            sim.radio.packet_toa_s(flood) + protocol.flood_base_delay_s
            + protocol.flood_jitter_s + 0.35
            + sim.radio.packet_toa_s(ack)
        ) + 3.0

        self.assertGreaterEqual(protocol.flood_round_trip_bound_s(), full_cost)

    def test_ninth_concurrent_flood_window_reports_capacity_fallback(self):
        class DestinationOnlySimulator(TraceSimulator):
            def try_receive(self, tx, receiver):
                if receiver != 9:
                    return None
                return Simulator.try_receive(self, tx, receiver)

        protocol = build_protocol("meshecho-dbr")
        sim = DestinationOnlySimulator(
            [Node(i, 0.0, 0.0) for i in range(10)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=1, independent_random_streams=True,
        )
        for src in range(9):
            sim.schedule(1.0 + 0.2 * src, "app_send", (src, 9, src + 1))

        metrics = sim.run(6.0)

        self.assertEqual(metrics.unicast_deliveries, 9)
        overflow = [event for event in protocol.action_events
                    if event.get("event") == "dbr_feedback_capacity_overflow"]
        self.assertEqual([event["flow_id"] for event in overflow], [9])
        acks = [tx.packet for tx in sim.tx_history
                if tx.sender == 9 and tx.packet.kind == "ACK"
                and tx.packet.flow_id == 9]
        self.assertEqual(len(acks), 1)
        self.assertEqual(acks[0].alternate_path, ())

    def test_canceled_backup_request_reconsiders_flood_when_radio_is_free(self):
        protocol = build_protocol("meshecho-dbr")
        protocol.flood_base_delay_s = 0.5
        protocol.flood_jitter_s = 0.0
        sim = TraceSimulator(
            [Node(i, i * 10.0, 0.0) for i in range(4)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 3, 1))
        sim.schedule(5.0, "app_send", (0, 3, 2))

        def interrupt_after_guard():
            initial = next(tx for tx in sim.tx_history
                           if tx.sender == 0 and tx.packet.flow_id == 2
                           and tx.packet.kind == "DATA")
            guard_at = initial.start + 15.0
            sim.schedule(
                guard_at, "protocol_timer",
                lambda: setattr(sim.nodes[0], "tx_available_at", guard_at + 2.0),
            )

        sim.schedule(6.0, "protocol_timer", interrupt_after_guard)
        sim.run(36.0)

        recoveries = [tx for tx in sim.tx_history
                      if tx.sender == 0 and tx.packet.flow_id == 2
                      and tx.packet.repair_index is not None]
        self.assertEqual([(tx.packet.kind, tx.packet.repair_index)
                          for tx in recoveries], [("FLOOD", 2)])
        self.assertGreaterEqual(recoveries[0].start, 22.0)
        guard = next(event for event in protocol.action_events
                     if event.get("event") == "dbr_guard"
                     and event["flow_id"] == 2)
        self.assertTrue(guard["decision_admitted"])
        self.assertEqual(guard["selected_action"], "B")
        drops = [event for event in protocol.action_events
                 if event.get("event") == "dbr_recovery_request_drop"
                 and event["flow_id"] == 2]
        self.assertEqual([(event["action"], event["reason"])
                          for event in drops], [("B", "source-queued")])

    def test_source_busy_at_guard_rechecks_flood_when_idle(self):
        protocol = build_protocol("meshecho-dbr")
        protocol.flood_base_delay_s = 0.5
        protocol.flood_jitter_s = 0.0
        sim = TraceSimulator(
            [Node(i, i * 10.0, 0.0) for i in range(4)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 3, 1))
        sim.schedule(5.0, "app_send", (0, 3, 2))
        sim.schedule(
            19.9, "protocol_timer",
            lambda: setattr(sim.nodes[0], "tx_available_at", 22.0),
        )

        sim.run(36.0)

        guard = next(event for event in protocol.action_events
                     if event.get("event") == "dbr_guard"
                     and event["flow_id"] == 2)
        self.assertEqual((guard["selected_action"], guard["reason"]),
                         ("none", "source-busy"))
        recoveries = [tx for tx in sim.tx_history
                      if tx.sender == 0 and tx.packet.flow_id == 2
                      and tx.packet.repair_index is not None]
        self.assertEqual([(tx.packet.kind, tx.packet.repair_index)
                          for tx in recoveries], [("FLOOD", 2)])
        self.assertGreaterEqual(recoveries[0].start, 22.0)

    def test_late_initial_ack_cancels_a_deferred_flood_retry(self):
        protocol = build_protocol("meshecho-dbr")
        protocol.flood_base_delay_s = 0.5
        protocol.flood_jitter_s = 0.0
        sim = DropBackupSimulator(
            [Node(i, i * 10.0, 0.0) for i in range(4)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 3, 1))
        sim.schedule(5.0, "app_send", (0, 3, 2))
        sim.schedule(
            21.9, "protocol_timer",
            lambda: setattr(sim.nodes[0], "tx_available_at", 24.0),
        )
        late_ack = Packet(
            kind="ACK", flow_id=2, origin=3, final_dst=0, ttl=6,
            created_at=22.7, protocol=protocol.name, request_id=2,
            path=(0, 3), path_index=0, app_payload=False,
        )
        sim.schedule(
            22.7, "protocol_timer",
            lambda: sim.transmit_later(3, late_ack, delay_s=0.0),
        )

        metrics = sim.run(36.0)

        self.assertIsNotNone(metrics.flows[2].acked_at)
        self.assertFalse(any(
            tx.sender == 0 and tx.packet.flow_id == 2
            and tx.packet.kind == "FLOOD" and tx.packet.repair_index == 2
            for tx in sim.tx_history
        ))

    def test_old_generation_backup_ack_cannot_replace_a_newer_flood_commit(self):
        class ReorderedAcksSimulator(TraceSimulator):
            def try_receive(self, tx, receiver):
                packet = tx.packet
                if (receiver == 3 and tx.sender == 0 and packet.flow_id == 3
                        and packet.kind == "DATA" and packet.repair_index is None):
                    return None
                if (receiver == 0 and packet.kind == "ACK"
                        and ((packet.flow_id == 2 and tx.start < 24.5)
                             or (packet.flow_id == 3
                                 and packet.repair_index == 3
                                 and tx.start < 25.0))):
                    return None
                return super().try_receive(tx, receiver)

        protocol = build_protocol("meshecho-dbr")
        protocol.flood_base_delay_s = 0.5
        protocol.flood_jitter_s = 0.0
        sim = ReorderedAcksSimulator(
            [Node(i, i * 10.0, 0.0) for i in range(4)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        for when, flow_id in ((1.0, 2), (5.0, 1), (9.0, 3)):
            sim.schedule(when, "app_send", (0, 3, flow_id))
        newer_flood_ack = Packet(
            kind="ACK", flow_id=2, origin=3, final_dst=0, ttl=6,
            created_at=24.5, protocol=protocol.name, request_id=2,
            path=(0, 3), path_index=0, app_payload=False,
        )
        old_backup_ack = Packet(
            kind="ACK", flow_id=3, origin=3, final_dst=0, ttl=6,
            created_at=25.0, protocol=protocol.name, request_id=3,
            path=(0, 2, 3), path_index=0, app_payload=False,
            repair_index=3,
        )
        sim.schedule(24.5, "protocol_timer",
                     lambda: sim.transmit_later(3, newer_flood_ack, 0.0))
        sim.schedule(25.0, "protocol_timer",
                     lambda: sim.transmit_later(2, old_backup_ack, 0.0))

        metrics = sim.run(27.0)

        self.assertIsNotNone(metrics.flows[2].acked_at)
        self.assertIsNotNone(metrics.flows[3].acked_at)
        self.assertEqual(protocol.route_cache[0][3].path, (0, 3))
        self.assertEqual(protocol.source_state(0, 3).last_commit_flow, 2)

    def test_coincident_idle_rechecks_log_every_busy_flood_cancellation(self):
        class MissingInitialDataSimulator(TraceSimulator):
            def try_receive(self, tx, receiver):
                if (receiver == 3 and tx.sender == 0
                        and tx.packet.flow_id in {2, 3, 4}
                        and tx.packet.kind == "DATA"
                        and tx.packet.repair_index is None):
                    return None
                return super().try_receive(tx, receiver)

        protocol = build_protocol("meshecho-dbr-fixed-f")
        protocol.flood_base_delay_s = 0.5
        protocol.flood_jitter_s = 0.0
        sim = MissingInitialDataSimulator(
            [Node(i, i * 10.0, 0.0) for i in range(4)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        for when, flow_id in ((1.0, 1), (5.0, 2), (6.0, 3), (7.0, 4)):
            sim.schedule(when, "app_send", (0, 3, flow_id))
        sim.schedule(
            19.0, "protocol_timer",
            lambda: setattr(sim.nodes[0], "tx_available_at", 24.0),
        )

        sim.run(38.0)

        guards = [event for event in protocol.action_events
                  if event.get("event") == "dbr_guard"
                  and event["flow_id"] in {2, 3, 4}]
        self.assertEqual({event["flow_id"] for event in guards}, {2, 3, 4})
        self.assertTrue(all(event["reason"] == "source-busy" for event in guards))
        floods = [tx for tx in sim.tx_history
                  if tx.sender == 0 and tx.packet.kind == "FLOOD"
                  and tx.packet.repair_index == 2]
        self.assertEqual({flow_id: sum(tx.packet.flow_id == flow_id for tx in floods)
                          for flow_id in (2, 3, 4)}, {2: 1, 3: 1, 4: 1})
        self.assertEqual(sum(abs(tx.start - 24.0) < 1e-9 for tx in floods), 1)
        cancellations = [event for event in protocol.action_events
                         if event.get("event") == "dbr_recovery_request_drop"
                         and event["flow_id"] in {2, 3, 4}]
        self.assertEqual(
            [(event["flow_id"], event["action"], event["reason"])
             for event in cancellations],
            [(3, "F", "source-queued"), (4, "F", "source-queued"),
             (4, "F", "source-queued")],
        )

    def test_initial_ack_physical_receive_at_guard_prevents_recovery(self):
        protocol = build_protocol("meshecho-dbr")
        protocol.flood_base_delay_s = 0.5
        protocol.flood_jitter_s = 0.0
        sim = TraceSimulator(
            [Node(i, i * 10.0, 0.0) for i in range(4)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 3, 1))
        sim.schedule(5.0, "app_send", (0, 3, 2))

        def queue_late_ack():
            initial = next(tx for tx in sim.tx_history
                           if tx.sender == 0 and tx.packet.flow_id == 2
                           and tx.packet.kind == "DATA")
            guard_at = initial.start + 15.0
            ack = Packet(
                kind="ACK", flow_id=2, origin=3, final_dst=0, ttl=6,
                created_at=guard_at, protocol=protocol.name, request_id=2,
                path=initial.packet.path, path_index=0, app_payload=False,
            )
            sim.schedule(
                guard_at - sim.radio.packet_toa_s(ack), "protocol_timer",
                lambda: sim.transmit_later(3, ack, delay_s=0.0),
            )

        sim.schedule(6.0, "protocol_timer", queue_late_ack)
        metrics = sim.run(36.0)

        initial = next(tx for tx in sim.tx_history
                       if tx.sender == 0 and tx.packet.flow_id == 2
                       and tx.packet.kind == "DATA")
        ack_tx = next(tx for tx in sim.tx_history
                      if tx.sender == 3 and tx.packet.flow_id == 2
                      and tx.packet.kind == "ACK")
        self.assertEqual(ack_tx.end, initial.start + 15.0)
        self.assertEqual(metrics.flows[2].acked_at, ack_tx.end)
        self.assertFalse(any(event.get("event") == "dbr_guard"
                             and event["flow_id"] == 2
                             for event in protocol.action_events))
        self.assertFalse(any(tx.sender == 0 and tx.packet.flow_id == 2
                             and tx.packet.repair_index in {2, 3}
                             for tx in sim.tx_history))

    def test_backup_ack_at_guard_wins_and_late_initial_ack_cannot_rollback(self):
        protocol = build_protocol("meshecho-dbr")
        protocol.flood_base_delay_s = 0.5
        protocol.flood_jitter_s = 0.0
        sim = DeferredBackupAckSimulator(
            [Node(i, i * 10.0, 0.0) for i in range(4)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 3, 1))
        sim.schedule(5.0, "app_send", (0, 3, 2))

        def release_at_backup_guard():
            backup = next(tx for tx in sim.tx_history
                          if tx.sender == 0 and tx.packet.flow_id == 2
                          and tx.packet.repair_index == 3)
            relay_ack = next(tx.packet for tx in sim.tx_history
                             if tx.sender == 2 and tx.packet.kind == "ACK"
                             and tx.packet.flow_id == 2
                             and tx.packet.repair_index == 3)
            guard_at = backup.start + 2.0
            def release():
                sim.release_backup_ack = True
                sim.transmit_later(2, relay_ack, delay_s=0.0)
            sim.schedule(guard_at - sim.radio.packet_toa_s(relay_ack),
                         "protocol_timer", release)

        sim.schedule(21.0, "protocol_timer", release_at_backup_guard)
        late_initial_ack = Packet(
            kind="ACK", flow_id=2, origin=3, final_dst=0, ttl=6,
            created_at=23.0, protocol=protocol.name, request_id=2,
            path=(0, 3), path_index=0, app_payload=False,
        )
        sim.schedule(23.0, "protocol_timer",
                     lambda: sim.transmit_later(3, late_initial_ack, 0.0))

        metrics = sim.run(36.0)

        backup = next(tx for tx in sim.tx_history
                      if tx.sender == 0 and tx.packet.flow_id == 2
                      and tx.packet.repair_index == 3)
        received_ack = [event for event in protocol.action_events
                        if event.get("event") == "dbr_source_ack_rx"
                        and event["flow_id"] == 2 and event["accepted"]]
        self.assertEqual(metrics.flows[2].acked_at, backup.start + 2.0)
        self.assertEqual(len(received_ack), 1)
        self.assertEqual(received_ack[0]["path"], (0, 2, 3))
        self.assertEqual(protocol.route_cache[0][3].path, (0, 2, 3))
        self.assertEqual(protocol.source_state(0, 3).last_commit_flow, 2)
        self.assertFalse(any(tx.sender == 0 and tx.packet.flow_id == 2
                             and tx.packet.kind == "FLOOD"
                             and tx.packet.repair_index == 2
                             for tx in sim.tx_history))

    def test_initial_ack_at_backup_guard_wins_over_later_backup_ack(self):
        protocol = build_protocol("meshecho-dbr")
        protocol.flood_base_delay_s = 0.5
        protocol.flood_jitter_s = 0.0
        sim = DeferredBackupAckSimulator(
            [Node(i, i * 10.0, 0.0) for i in range(4)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 3, 1))
        sim.schedule(5.0, "app_send", (0, 3, 2))

        def order_acks_around_guard():
            backup = next(tx for tx in sim.tx_history
                          if tx.sender == 0 and tx.packet.flow_id == 2
                          and tx.packet.repair_index == 3)
            relay_ack = next(tx.packet for tx in sim.tx_history
                             if tx.sender == 2 and tx.packet.kind == "ACK"
                             and tx.packet.flow_id == 2
                             and tx.packet.repair_index == 3)
            guard_at = backup.start + 2.0
            initial_ack = Packet(
                kind="ACK", flow_id=2, origin=3, final_dst=0, ttl=6,
                created_at=guard_at, protocol=protocol.name, request_id=2,
                path=(0, 3), path_index=0, app_payload=False,
            )
            sim.schedule(guard_at - sim.radio.packet_toa_s(initial_ack),
                         "protocol_timer",
                         lambda: sim.transmit_later(3, initial_ack, 0.0))
            def release_backup_ack():
                sim.release_backup_ack = True
                sim.transmit_later(2, relay_ack, 0.0)
            sim.schedule(guard_at + 0.3, "protocol_timer", release_backup_ack)

        sim.schedule(21.0, "protocol_timer", order_acks_around_guard)
        metrics = sim.run(36.0)

        backup = next(tx for tx in sim.tx_history
                      if tx.sender == 0 and tx.packet.flow_id == 2
                      and tx.packet.repair_index == 3)
        self.assertEqual(metrics.flows[2].acked_at, backup.start + 2.0)
        self.assertEqual(protocol.route_cache[0][3].path, (0, 3))
        self.assertEqual(protocol.source_state(0, 3).last_commit_flow, 1)
        self.assertFalse(any(tx.sender == 0 and tx.packet.flow_id == 2
                             and tx.packet.kind == "FLOOD"
                             and tx.packet.repair_index == 2
                             for tx in sim.tx_history))
        late_backup = [event for event in protocol.action_events
                       if event.get("event") == "dbr_source_ack_rx"
                       and event["flow_id"] == 2]
        self.assertEqual([event["accepted"] for event in late_backup], [False])

    def test_flood_ack_first_rejects_late_backup_and_initial_acks(self):
        protocol = build_protocol("meshecho-dbr")
        protocol.flood_base_delay_s = 0.5
        protocol.flood_jitter_s = 0.0
        sim = DropBackupSimulator(
            [Node(i, i * 10.0, 0.0) for i in range(4)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 3, 1))
        sim.schedule(5.0, "app_send", (0, 3, 2))
        stale_backup_ack = Packet(
            kind="ACK", flow_id=2, origin=3, final_dst=0, ttl=6,
            created_at=26.0, protocol=protocol.name, request_id=2,
            path=(0, 2, 3), path_index=0, app_payload=False,
            repair_index=3,
        )
        stale_initial_ack = Packet(
            kind="ACK", flow_id=2, origin=3, final_dst=0, ttl=6,
            created_at=27.0, protocol=protocol.name, request_id=2,
            path=(0, 3), path_index=0, app_payload=False,
        )
        sim.schedule(26.0, "protocol_timer",
                     lambda: sim.transmit_later(2, stale_backup_ack, 0.0))
        sim.schedule(27.0, "protocol_timer",
                     lambda: sim.transmit_later(3, stale_initial_ack, 0.0))

        metrics = sim.run(36.0)

        flood_ack = next(tx for tx in sim.tx_history
                         if tx.sender == 3 and tx.packet.kind == "ACK"
                         and tx.packet.flow_id == 2
                         and tx.packet.repair_index == 2)
        self.assertEqual(metrics.flows[2].acked_at, flood_ack.end)
        self.assertEqual(protocol.route_cache[0][3].path, (0, 3))
        self.assertEqual(protocol.source_state(0, 3).last_commit_flow, 2)
        commits = [event for event in protocol.action_events
                   if event.get("event") == "commit" and event["flow_id"] == 2]
        self.assertEqual([(event["action"], event["path"])
                          for event in commits], [("F-recovery", (0, 3))])
        stale_backup = [event for event in protocol.action_events
                        if event.get("event") == "dbr_source_ack_rx"
                        and event["flow_id"] == 2]
        self.assertEqual([event["accepted"] for event in stale_backup], [False])

    def test_old_initial_ack_confirms_flow_without_rolling_back_newer_flood(self):
        class NewerFloodWinsSimulator(TraceSimulator):
            def try_receive(self, tx, receiver):
                packet = tx.packet
                if (receiver == 3 and tx.sender == 0
                        and packet.flow_id in {2, 3}
                        and packet.kind == "DATA"
                        and packet.repair_index is None):
                    return None
                if (receiver == 0 and packet.kind == "ACK"
                        and packet.flow_id == 2
                        and packet.repair_index == 2):
                    return None
                return super().try_receive(tx, receiver)

        protocol = build_protocol("meshecho-dbr-fixed-f")
        protocol.flood_base_delay_s = 0.5
        protocol.flood_jitter_s = 0.0
        sim = NewerFloodWinsSimulator(
            [Node(i, i * 10.0, 0.0) for i in range(4)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        for when, flow_id in ((1.0, 1), (5.0, 2), (10.0, 3)):
            sim.schedule(when, "app_send", (0, 3, flow_id))
        old_initial_ack = Packet(
            kind="ACK", flow_id=2, origin=3, final_dst=0, ttl=6,
            created_at=29.0, protocol=protocol.name, request_id=2,
            path=(0, 3), path_index=0, app_payload=False,
        )
        sim.schedule(29.0, "protocol_timer",
                     lambda: sim.transmit_later(3, old_initial_ack, 0.0))

        metrics = sim.run(31.0)

        newer_commit = next(event for event in protocol.action_events
                            if event.get("event") == "commit"
                            and event["flow_id"] == 3
                            and event["action"] == "F-recovery")
        self.assertLess(newer_commit["time"], metrics.flows[2].acked_at)
        self.assertEqual(protocol.source_state(0, 3).last_commit_flow, 3)
        self.assertEqual(protocol.route_cache[0][3].path, newer_commit["path"])
        old_ack_events = [event for event in protocol.action_events
                          if event.get("event") == "dhr_source_ack_rx"
                          and event["flow_id"] == 2
                          and event["repair_index"] is None]
        self.assertEqual([event["accepted"] for event in old_ack_events], [True])


if __name__ == "__main__":
    unittest.main()
