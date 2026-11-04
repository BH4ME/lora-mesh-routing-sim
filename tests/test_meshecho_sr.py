import unittest

from lora_mesh_sim import Node, RadioConfig, Simulator, build_protocol


class MeshEchoSRTest(unittest.TestCase):
    def test_queued_discovery_wait_starts_with_source_rreq_transmission(self) -> None:
        protocol = build_protocol("meshecho-sr")
        sim = Simulator(
            [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        for flow_id, when in enumerate((1.0, 20.0, 200.0), start=1):
            sim.schedule(when, "app_send", (0, 1, flow_id))
        sim.schedule(
            199.0, "protocol_timer",
            lambda: setattr(sim.nodes[0], "tx_available_at", 220.0),
        )

        sim.run(215.0)

        self.assertEqual(protocol.flow_actions[3], "D")
        self.assertTrue(any(
            start == 220.0 for start, _ in sim.metrics.transmission_intervals
        ))
        self.assertFalse(any(
            event["event"] == "timeout" and event["flow_id"] == 3
            for event in protocol.action_events
        ))
        self.assertEqual(protocol.destination_state[(0, 1)].pending_discovery_flow, 3)

    def test_six_hop_discovery_waits_for_valid_destination_window_and_rrep(self) -> None:
        class LineSimulator(Simulator):
            def try_receive(self, tx, receiver):
                if abs(tx.sender - receiver) != 1:
                    return None
                return super().try_receive(tx, receiver)

        protocol = build_protocol("meshecho-sr")
        sim = LineSimulator(
            [Node(node_id, node_id * 100.0, 0.0) for node_id in range(7)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=31, max_hops=6, independent_random_streams=True,
            matched_rreq_timing=True,
        )
        for flow_id, when in enumerate((1.0, 20.0, 200.0), start=1):
            sim.schedule(when, "app_send", (0, 6, flow_id))

        metrics = sim.run(240.0)

        self.assertEqual(protocol.flow_actions[3], "D")
        self.assertTrue(any(
            event["event"] == "candidate" and event["flow_id"] == 3
            for event in protocol.action_events
        ))
        self.assertFalse(any(
            event["event"] == "timeout" and event["flow_id"] == 3
            for event in protocol.action_events
        ))
        self.assertIsNotNone(metrics.flows[3].acked_at)

    def test_first_unicast_floods_and_confirms_realized_route_only_after_ack(self) -> None:
        protocol = build_protocol("meshecho-sr")
        sim = Simulator(
            [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0),
            protocol,
            seed=17,
            max_hops=6,
            independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 1, 1))

        metrics = sim.run(20.0)

        self.assertIsNotNone(metrics.flows[1].acked_at)
        self.assertEqual(protocol.route_cache[0][1].path, (0, 1))
        self.assertEqual(
            [event["action"] for event in protocol.action_events if event["event"] == "decision"],
            ["F"],
        )

    def test_ack_confirmed_route_is_reused_for_next_flow(self) -> None:
        protocol = build_protocol("meshecho-sr")
        sim = Simulator(
            [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0),
            protocol,
            seed=17,
            max_hops=6,
            independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 1, 1))
        sim.schedule(3.0, "app_send", (0, 1, 2))

        metrics = sim.run(20.0)

        self.assertIsNotNone(metrics.flows[2].acked_at)
        self.assertEqual(
            [event["action"] for event in protocol.action_events if event["event"] == "decision"],
            ["F", "R"],
        )
        self.assertEqual(metrics.data_tx, 2)
        self.assertEqual(metrics.route_cache_hits, 1)

    def test_aging_confirmed_route_triggers_one_prefailure_discovery(self) -> None:
        protocol = build_protocol("meshecho-sr")
        sim = Simulator(
            [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0),
            protocol,
            seed=17,
            max_hops=6,
            independent_random_streams=True,
            matched_rreq_timing=True,
        )
        for flow_id, when in enumerate((1.0, 20.0, 200.0), start=1):
            sim.schedule(when, "app_send", (0, 1, flow_id))

        metrics = sim.run(240.0)

        self.assertEqual(
            [event["action"] for event in protocol.action_events if event["event"] == "decision"],
            ["F", "R", "D"],
        )
        self.assertEqual(metrics.route_discovery_attempts, 1)
        self.assertIsNotNone(metrics.flows[3].acked_at)
        self.assertGreater(protocol.route_cache[0][1].created_at, 200.0)
        candidate = next(event for event in protocol.action_events
                         if event["event"] == "candidate" and event["flow_id"] == 3)
        commit = next(event for event in protocol.action_events
                      if event["event"] == "commit" and event["flow_id"] == 3)
        self.assertEqual(candidate["old_path"], (0, 1))
        self.assertFalse(candidate["different_path"])
        self.assertFalse(commit["replaced_confirmed_path"])

    def test_failed_shadow_discovery_reuses_old_route_without_refreshing_commit(self) -> None:
        class NoDiscoverySimulator(Simulator):
            source_data_starts = None

            def try_receive(self, tx, receiver):
                if tx.packet.kind == "RREQ" and tx.packet.flow_id == 3:
                    return None
                return super().try_receive(tx, receiver)

            def begin_transmission(self, sender, packet, pending):
                super().begin_transmission(sender, packet, pending)
                if sender == 0 and packet.flow_id == 3 and packet.kind in {"DATA", "FLOOD"}:
                    if self.source_data_starts is None:
                        self.source_data_starts = []
                    self.source_data_starts.append(self.transmissions[-1].start)

        protocol = build_protocol("meshecho-sr")
        sim = NoDiscoverySimulator(
            [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0),
            protocol,
            seed=17,
            max_hops=6,
            independent_random_streams=True,
        )
        for flow_id, when in enumerate((1.0, 20.0, 200.0), start=1):
            sim.schedule(when, "app_send", (0, 1, flow_id))

        sim.run(240.0)

        self.assertEqual(protocol.flow_actions[3], "D")
        self.assertIsNotNone(sim.metrics.flows[3].acked_at)
        self.assertEqual(len(sim.source_data_starts), 1)
        self.assertGreaterEqual(sim.source_data_starts[0], 210.0)
        self.assertLess(protocol.route_cache[0][1].created_at, 20.0)
        self.assertFalse(any(
            event["event"] == "commit" and event["flow_id"] == 3
            for event in protocol.action_events
        ))

    def test_two_route_ack_timeouts_trigger_a_flood(self) -> None:
        class DropRouteAcks(Simulator):
            def try_receive(self, tx, receiver):
                if tx.packet.kind == "ACK" and tx.packet.flow_id in (2, 3) and receiver == 0:
                    return None
                return super().try_receive(tx, receiver)

        protocol = build_protocol("meshecho-sr")
        sim = DropRouteAcks(
            [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0),
            protocol,
            seed=17,
            max_hops=6,
            independent_random_streams=True,
        )
        for flow_id, when in enumerate((1.0, 20.0, 40.0, 60.0), start=1):
            sim.schedule(when, "app_send", (0, 1, flow_id))

        sim.run(100.0)

        self.assertEqual(
            [event["action"] for event in protocol.action_events if event["event"] == "decision"],
            ["F", "R", "R", "F"],
        )
        self.assertEqual(protocol.destination_state[(0, 1)].consecutive_r_misses, 0)

    def test_two_cold_flood_ack_misses_trigger_budgeted_discovery(self) -> None:
        class DropColdAcks(Simulator):
            def try_receive(self, tx, receiver):
                if tx.packet.kind == "ACK" and tx.packet.flow_id in (1, 2) and receiver == 0:
                    return None
                return super().try_receive(tx, receiver)

        protocol = build_protocol("meshecho-sr")
        sim = DropColdAcks(
            [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0),
            protocol,
            seed=17,
            max_hops=6,
            independent_random_streams=True,
        )
        for flow_id, when in enumerate((1.0, 20.0, 40.0), start=1):
            sim.schedule(when, "app_send", (0, 1, flow_id))

        sim.run(80.0)

        decisions = [event for event in protocol.action_events if event["event"] == "decision"]
        self.assertEqual([event["action"] for event in decisions], ["F", "F", "D"])
        self.assertEqual(decisions[2]["reason"], "repeated-cold-misses")
        self.assertIsNotNone(sim.metrics.flows[3].acked_at)

    def test_matched_variants_replace_the_same_shadow_trigger(self) -> None:
        expected = {
            "meshecho-sr": "D",
            "meshecho-sr-fr": "R",
            "meshecho-sr-trigger-f": "F",
            "meshecho-sr-periodic": "D",
        }
        for name, last_action in expected.items():
            with self.subTest(name=name):
                protocol = build_protocol(name)
                self.assertEqual(protocol.name, name)
                sim = Simulator(
                    [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
                    RadioConfig(sf=7, shadow_sigma_db=0.0),
                    protocol,
                    seed=17,
                    max_hops=6,
                    independent_random_streams=True,
                )
                for flow_id, when in enumerate((1.0, 20.0, 200.0), start=1):
                    sim.schedule(when, "app_send", (0, 1, flow_id))
                sim.run(240.0)
                self.assertEqual(
                    [event["action"] for event in protocol.action_events
                     if event["event"] == "decision"],
                    ["F", "R", last_action],
                )

    def test_periodic_refresh_does_not_require_repeated_demand(self) -> None:
        for name, last_action in (("meshecho-sr", "R"),
                                  ("meshecho-sr-periodic", "D")):
            with self.subTest(name=name):
                protocol = build_protocol(name)
                sim = Simulator(
                    [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
                    RadioConfig(sf=7, shadow_sigma_db=0.0),
                    protocol,
                    seed=17,
                    max_hops=6,
                    independent_random_streams=True,
                )
                sim.schedule(1.0, "app_send", (0, 1, 1))
                sim.schedule(200.0, "app_send", (0, 1, 2))
                sim.run(240.0)
                self.assertEqual(
                    [event["action"] for event in protocol.action_events
                     if event["event"] == "decision"],
                    ["F", last_action],
                )

    def test_candidate_data_without_ack_retains_confirmed_old_route(self) -> None:
        class DropCandidateAck(Simulator):
            def try_receive(self, tx, receiver):
                if tx.packet.kind == "ACK" and tx.packet.flow_id == 3 and receiver == 0:
                    return None
                return super().try_receive(tx, receiver)

        protocol = build_protocol("meshecho-sr")
        sim = DropCandidateAck(
            [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        for flow_id, when in enumerate((1.0, 20.0, 200.0), start=1):
            sim.schedule(when, "app_send", (0, 1, flow_id))

        sim.run(240.0)

        self.assertTrue(any(event["event"] == "candidate" and event["flow_id"] == 3
                            for event in protocol.action_events))
        self.assertIsNone(sim.metrics.flows[3].acked_at)
        self.assertLess(protocol.route_cache[0][1].created_at, 20.0)

    def test_lost_rrep_uses_one_old_route_data_after_source_deadline(self) -> None:
        class DropReply(Simulator):
            source_data = 0

            def try_receive(self, tx, receiver):
                if tx.packet.kind == "RREP" and tx.packet.flow_id == 3 and receiver == 0:
                    return None
                return super().try_receive(tx, receiver)

            def begin_transmission(self, sender, packet, pending):
                super().begin_transmission(sender, packet, pending)
                if sender == 0 and packet.flow_id == 3 and packet.kind in {"DATA", "FLOOD"}:
                    self.source_data += 1

        protocol = build_protocol("meshecho-sr")
        sim = DropReply(
            [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        for flow_id, when in enumerate((1.0, 20.0, 200.0), start=1):
            sim.schedule(when, "app_send", (0, 1, flow_id))

        sim.run(240.0)

        self.assertEqual(sim.source_data, 1)
        self.assertIsNotNone(sim.metrics.flows[3].acked_at)
        self.assertLess(protocol.route_cache[0][1].created_at, 20.0)
        self.assertTrue(any(event["event"] == "timeout"
                            and event.get("reason") == "rrep-timeout"
                            for event in protocol.action_events))

    def test_queued_source_data_is_not_an_ack_miss_before_transmission(self) -> None:
        protocol = build_protocol("meshecho-sr")
        sim = Simulator(
            [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.nodes[0].tx_available_at = 100.0
        sim.schedule(1.0, "app_send", (0, 1, 1))

        sim.run(40.0)

        self.assertEqual(sim.metrics.transmission_intervals[0][0], 100.0)
        self.assertEqual(protocol.destination_state[(0, 1)].consecutive_f_misses, 0)
        self.assertFalse(any(event["event"] == "timeout"
                             and event.get("reason") == "source-ack-timeout"
                             for event in protocol.action_events))

    def test_late_ack_before_application_deadline_corrects_route_timeout(self) -> None:
        class DelayReply(Simulator):
            def transmit_later(self, sender, packet, delay_s, pending=None):
                if packet.kind == "ACK" and packet.flow_id == 2:
                    delay_s += 16.0
                return super().transmit_later(sender, packet, delay_s, pending)

        protocol = build_protocol("meshecho-sr")
        sim = DelayReply(
            [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        for flow_id, when in enumerate((1.0, 20.0, 37.0), start=1):
            sim.schedule(when, "app_send", (0, 1, flow_id))

        sim.run(80.0)

        self.assertIsNotNone(sim.metrics.flows[2].acked_at)
        self.assertEqual(protocol.destination_state[(0, 1)].consecutive_r_misses, 0)
        self.assertFalse(protocol.destination_state[(0, 1)].had_r_miss_since_commit)
        self.assertEqual(protocol.flow_actions[3], "R")

    def test_ack_after_application_deadline_is_not_counted_or_committed(self) -> None:
        class DelayReply(Simulator):
            def transmit_later(self, sender, packet, delay_s, pending=None):
                if packet.kind == "ACK" and packet.flow_id == 2:
                    delay_s += 35.0
                return super().transmit_later(sender, packet, delay_s, pending)

        protocol = build_protocol("meshecho-sr")
        sim = DelayReply(
            [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 1, 1))
        sim.schedule(20.0, "app_send", (0, 1, 2))

        sim.run(80.0)

        self.assertIsNone(sim.metrics.flows[2].acked_at)
        self.assertLess(protocol.route_cache[0][1].created_at, 20.0)
        self.assertTrue(protocol.destination_state[(0, 1)].had_r_miss_since_commit)

    def test_source_keeps_at_most_eight_destinations_and_two_send_times_each(self) -> None:
        protocol = build_protocol("meshecho-sr")
        sim = Simulator(
            [Node(node_id, float(node_id * 10), 0.0) for node_id in range(11)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        for flow_id, dst in enumerate(range(1, 11), start=1):
            sim.now = float(flow_id)
            protocol.send_app(0, dst, flow_id)

        self.assertLessEqual(sum(src == 0 for src, _ in protocol.destination_state), 8)
        self.assertNotIn((0, 1), protocol.destination_state)
        for flow_id in range(11, 20):
            sim.now = float(flow_id)
            protocol.send_app(0, 10, flow_id)
        self.assertEqual(protocol.destination_state[(0, 10)].send_times, [18.0, 19.0])

    def test_late_ack_for_older_route_flow_does_not_erase_newer_misses(self) -> None:
        class MixedFeedback(Simulator):
            def transmit_later(self, sender, packet, delay_s, pending=None):
                if packet.kind == "ACK" and packet.flow_id == 2:
                    delay_s += 23.0
                return super().transmit_later(sender, packet, delay_s, pending)

            def try_receive(self, tx, receiver):
                if tx.packet.kind == "ACK" and tx.packet.flow_id in (3, 4) and receiver == 0:
                    return None
                return super().try_receive(tx, receiver)

        protocol = build_protocol("meshecho-sr")
        sim = MixedFeedback(
            [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        for flow_id, when in enumerate((1.0, 20.0, 25.0, 45.0, 65.0), start=1):
            sim.schedule(when, "app_send", (0, 1, flow_id))

        sim.run(100.0)

        self.assertIsNotNone(sim.metrics.flows[2].acked_at)
        self.assertEqual(protocol.flow_actions[5], "F")


if __name__ == "__main__":
    unittest.main()
