import unittest

from lora_mesh_sim import Node, RadioConfig, Simulator, build_protocol


class MeshEchoDHRTest(unittest.TestCase):
    def test_lost_initial_r_data_is_recovered_once_on_the_same_flow(self) -> None:
        class DropInitialRouteData(Simulator):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.sent_packets = []

            def begin_transmission(self, sender, packet, pending):
                before = self.metrics.tx_count
                super().begin_transmission(sender, packet, pending)
                if self.metrics.tx_count > before:
                    self.sent_packets.append(packet)

            def try_receive(self, tx, receiver):
                if (tx.packet.kind == "DATA" and tx.packet.flow_id == 2
                        and tx.packet.repair_index is None):
                    return None
                return super().try_receive(tx, receiver)

        protocol = build_protocol("meshecho-dhr")
        sim = DropInitialRouteData(
            [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 1, 1))
        sim.schedule(3.0, "app_send", (0, 1, 2))

        metrics = sim.run(34.0)

        self.assertEqual(protocol.flow_data_actions[2], "R")
        self.assertIsNotNone(metrics.flows[2].acked_at)
        self.assertLessEqual(metrics.flows[2].acked_at, 33.0)
        rescues = [
            event for event in protocol.action_events
            if event.get("event") == "dhr_recovery_tx" and event["flow_id"] == 2
        ]
        self.assertEqual(len(rescues), 1)
        self.assertEqual(rescues[0]["action"], "R")
        self.assertEqual(rescues[0]["repair_index"], 1)
        initial_ack = next(
            packet for packet in sim.sent_packets
            if packet.kind == "ACK" and packet.flow_id == 1
        )
        recovery_ack = next(
            packet for packet in sim.sent_packets
            if packet.kind == "ACK" and packet.flow_id == 2
        )
        self.assertEqual(recovery_ack.repair_index, 1)
        self.assertEqual(
            recovery_ack.wire_size_bytes(sim.radio.payload_bytes),
            initial_ack.wire_size_bytes(sim.radio.payload_bytes) + 1,
        )

    def test_stale_confirmed_route_uses_marked_flood_rescue(self) -> None:
        class DropInitialRouteData(Simulator):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.sent_packets = []

            def begin_transmission(self, sender, packet, pending):
                before = self.metrics.tx_count
                super().begin_transmission(sender, packet, pending)
                if self.metrics.tx_count > before:
                    self.sent_packets.append((sender, packet))

            def try_receive(self, tx, receiver):
                if (tx.packet.kind == "DATA" and tx.packet.flow_id == 2
                        and tx.packet.repair_index is None):
                    return None
                return super().try_receive(tx, receiver)

        protocol = build_protocol("meshecho-dhr")
        sim = DropInitialRouteData(
            [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 1, 1))
        sim.schedule(200.0, "app_send", (0, 1, 2))

        metrics = sim.run(231.0)

        self.assertEqual(protocol.flow_data_actions[2], "R")
        self.assertIsNotNone(metrics.flows[2].acked_at)
        rescues = [
            (sender, packet) for sender, packet in sim.sent_packets
            if packet.flow_id == 2 and packet.repair_index is not None
        ]
        self.assertEqual(len(rescues), 2)
        self.assertEqual(rescues[0][1].kind, "FLOOD")
        self.assertEqual(rescues[0][1].repair_index, 2)
        self.assertEqual(rescues[1][1].kind, "ACK")
        self.assertEqual(rescues[1][1].repair_index, 2)
        self.assertEqual(
            [(event["action"], event["repair_index"])
             for event in protocol.action_events
             if event.get("event") == "dhr_recovery_tx" and event["flow_id"] == 2],
            [("F", 2)],
        )

    def test_flood_rescue_commits_only_its_realized_alternate_path(self) -> None:
        class ChangePathAfterRouteFailure(Simulator):
            def try_receive(self, tx, receiver):
                packet = tx.packet
                if packet.flow_id == 1 and packet.kind in {"FLOOD", "ACK"}:
                    if (tx.sender, receiver) not in {
                        (0, 1), (1, 3), (3, 1), (1, 0),
                    }:
                        return None
                if packet.flow_id == 2:
                    if packet.kind == "DATA" and packet.repair_index is None:
                        return None
                    if packet.kind in {"FLOOD", "ACK"} and packet.repair_index == 2:
                        if (tx.sender, receiver) not in {
                            (0, 2), (2, 3), (3, 2), (2, 0),
                        }:
                            return None
                return super().try_receive(tx, receiver)

        protocol = build_protocol("meshecho-dhr")
        sim = ChangePathAfterRouteFailure(
            [Node(node_id, node_id * 10.0, 0.0) for node_id in range(4)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 3, 1))
        sim.schedule(200.0, "app_send", (0, 3, 2))

        metrics = sim.run(231.0)

        self.assertEqual(protocol.flow_sent_paths[2], (0, 1, 3))
        self.assertIsNotNone(metrics.flows[2].delivered_at)
        self.assertIsNotNone(metrics.flows[2].acked_at)
        self.assertEqual(protocol.route_cache[0][3].path, (0, 2, 3))
        self.assertTrue(any(
            event.get("event") == "commit" and event["flow_id"] == 2
            and event["path"] == (0, 2, 3)
            for event in protocol.action_events
        ))

    def test_busy_source_refuses_recovery_that_would_start_after_deadline(self) -> None:
        class DropInitialRouteData(Simulator):
            def try_receive(self, tx, receiver):
                if (tx.packet.kind == "DATA" and tx.packet.flow_id == 2
                        and tx.packet.repair_index is None):
                    return None
                return super().try_receive(tx, receiver)

        protocol = build_protocol("meshecho-dhr")
        sim = DropInitialRouteData(
            [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 1, 1))
        sim.schedule(3.0, "app_send", (0, 1, 2))
        sim.schedule(
            17.0, "protocol_timer",
            lambda: setattr(sim.nodes[0], "tx_available_at", 34.0),
        )

        sim.run(40.0)

        self.assertFalse(any(
            event.get("event") == "dhr_recovery_tx" and event["flow_id"] == 2
            for event in protocol.action_events
        ))
        self.assertTrue(any(
            event.get("event") == "dhr_guard" and event["flow_id"] == 2
            and not event["admitted"] and event["reason"] == "source-busy"
            for event in protocol.action_events
        ))

    def test_ninth_overlapping_r_flow_is_not_admitted_for_recovery(self) -> None:
        class DropRouteAcks(Simulator):
            def try_receive(self, tx, receiver):
                if (tx.packet.kind == "ACK" and tx.packet.flow_id >= 2
                        and receiver == 0):
                    return None
                return super().try_receive(tx, receiver)

        protocol = build_protocol("meshecho-dhr")
        sim = DropRouteAcks(
            [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 1, 1))
        for flow_id in range(2, 11):
            sim.schedule(3.0 + (flow_id - 2) * 0.01,
                         "app_send", (0, 1, flow_id))

        sim.run(40.0)

        self.assertEqual(
            [protocol.flow_actions[flow_id] for flow_id in range(2, 11)],
            ["R"] * 9,
        )
        self.assertTrue(any(
            event.get("event") == "dhr_guard" and event["flow_id"] == 10
            and not event["admitted"] and event["reason"] == "active-capacity"
            for event in protocol.action_events
        ))
        self.assertFalse(any(
            event.get("event") == "dhr_recovery_tx" and event["flow_id"] == 10
            for event in protocol.action_events
        ))

    def test_controls_share_guard_but_choose_their_declared_action(self) -> None:
        class DropInitialRouteData(Simulator):
            def try_receive(self, tx, receiver):
                if (tx.packet.kind == "DATA" and tx.packet.flow_id == 2
                        and tx.packet.repair_index is None):
                    return None
                return super().try_receive(tx, receiver)

        expected = {
            "meshecho-dhr": "F",
            "meshecho-dhr-none": "none",
            "meshecho-dhr-repeat": "R",
            "meshecho-dhr-flood": "F",
        }
        guard_times = []
        for name, action in expected.items():
            with self.subTest(name=name):
                protocol = build_protocol(name)
                sim = DropInitialRouteData(
                    [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
                    RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
                    seed=17, max_hops=6, independent_random_streams=True,
                )
                sim.schedule(1.0, "app_send", (0, 1, 1))
                sim.schedule(200.0, "app_send", (0, 1, 2))
                sim.run(231.0)

                self.assertEqual(protocol.flow_actions[2], "R")
                guard = next(
                    event for event in protocol.action_events
                    if event.get("event") == "dhr_guard" and event["flow_id"] == 2
                )
                self.assertTrue(guard["admitted"])
                self.assertEqual(guard["selected_action"], action)
                guard_times.append(guard["time"])
                rescues = [
                    event for event in protocol.action_events
                    if event.get("event") == "dhr_recovery_tx"
                    and event["flow_id"] == 2
                ]
                self.assertEqual(len(rescues), 0 if action == "none" else 1)
                if rescues:
                    self.assertEqual(rescues[0]["action"], action)
        self.assertEqual(len(set(guard_times)), 1)

    def test_lost_ack_does_not_count_repeated_data_as_new_delivery(self) -> None:
        class DropFirstRouteAck(Simulator):
            def try_receive(self, tx, receiver):
                if (tx.packet.kind == "ACK" and tx.packet.flow_id == 2
                        and tx.packet.repair_index is None and receiver == 0):
                    return None
                return super().try_receive(tx, receiver)

        protocol = build_protocol("meshecho-dhr")
        sim = DropFirstRouteAck(
            [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 1, 1))
        sim.schedule(3.0, "app_send", (0, 1, 2))

        metrics = sim.run(34.0)

        self.assertEqual(metrics.unicast_deliveries, 2)
        self.assertEqual(metrics.unicast_acks, 2)
        self.assertIsNotNone(metrics.flows[2].acked_at)
        self.assertEqual(
            [event["duplicate"] for event in protocol.action_events
             if event.get("event") == "dhr_destination_rx"
             and event["flow_id"] == 2],
            [False, True],
        )

    def test_late_original_ack_cannot_undo_flood_rescue_route_commit(self) -> None:
        class QueueOldAckOnOldPath(Simulator):
            def begin_transmission(self, sender, packet, pending):
                super().begin_transmission(sender, packet, pending)
                if (sender == 1 and packet.kind == "DATA"
                        and packet.flow_id == 2 and packet.repair_index is None):
                    self.nodes[1].tx_available_at = 225.0

            def try_receive(self, tx, receiver):
                packet = tx.packet
                if packet.flow_id == 1 and packet.kind in {"FLOOD", "ACK"}:
                    allowed = {(0, 1), (1, 3), (3, 1), (1, 0)}
                    if (tx.sender, receiver) not in allowed:
                        return None
                if packet.flow_id == 2:
                    if packet.repair_index is None and packet.kind in {"DATA", "ACK"}:
                        allowed = {(0, 1), (1, 3), (3, 1), (1, 0)}
                        if (tx.sender, receiver) not in allowed:
                            return None
                    if packet.repair_index == 2 and packet.kind in {"FLOOD", "ACK"}:
                        allowed = {(0, 2), (2, 3), (3, 2), (2, 0)}
                        if (tx.sender, receiver) not in allowed:
                            return None
                return super().try_receive(tx, receiver)

        protocol = build_protocol("meshecho-dhr")
        sim = QueueOldAckOnOldPath(
            [Node(node_id, node_id * 10.0, 0.0) for node_id in range(4)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 3, 1))
        sim.schedule(200.0, "app_send", (0, 3, 2))

        metrics = sim.run(231.0)

        self.assertLess(metrics.flows[2].delivered_at, 215.0)
        self.assertEqual(metrics.unicast_deliveries, 2)
        self.assertEqual(metrics.unicast_acks, 2)
        self.assertEqual(protocol.route_cache[0][3].path, (0, 2, 3))
        self.assertEqual(
            [(event["repair_index"], event["accepted"])
             for event in protocol.action_events
             if event.get("event") == "dhr_source_ack_rx"
             and event["flow_id"] == 2],
            [(2, True), (None, False)],
        )
        self.assertEqual(sum(
            event.get("event") == "commit" and event["flow_id"] == 2
            for event in protocol.action_events
        ), 1)

    def test_slow_phy_refuses_rescue_without_nominal_round_trip_slack(self) -> None:
        class DropInitialRouteData(Simulator):
            def try_receive(self, tx, receiver):
                if (tx.packet.kind == "DATA" and tx.packet.flow_id == 2
                        and tx.packet.repair_index is None):
                    return None
                return super().try_receive(tx, receiver)

        protocol = build_protocol("meshecho-dhr")
        sim = DropInitialRouteData(
            [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
            RadioConfig(sf=12, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 1, 1))
        sim.schedule(10.0, "app_send", (0, 1, 2))

        sim.run(50.0)

        self.assertEqual(protocol.flow_actions[2], "R")
        self.assertTrue(any(
            event.get("event") == "dhr_guard" and event["flow_id"] == 2
            and not event["admitted"] and event["reason"] == "deadline-budget"
            for event in protocol.action_events
        ))
        self.assertFalse(any(
            event.get("event") == "dhr_recovery_tx" and event["flow_id"] == 2
            for event in protocol.action_events
        ))


if __name__ == "__main__":
    unittest.main()
