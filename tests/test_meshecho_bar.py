"""Public packet-level behavior of the bounded alternate reverse ACK branch."""

import unittest

from lora_mesh_sim import Node, Packet, RadioConfig, Simulator, build_protocol


class DestinationFloodSimulator(Simulator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tx_history = []

    def begin_transmission(self, sender, packet, pending):
        before = self.metrics.tx_count
        super().begin_transmission(sender, packet, pending)
        if self.metrics.tx_count > before:
            self.tx_history.append(self.transmissions[-1])

    def try_receive(self, tx, receiver):
        if tx.packet.kind not in {"FLOOD", "DATA"} or receiver != 3:
            return None
        return super().try_receive(tx, receiver)


class MeshEchoBARTest(unittest.TestCase):
    def run_receipts(self, name, second_path=(0, 2), second_marker=None,
                     second_request_id=1, max_hops=4, second_delay=0.3):
        protocol = build_protocol(name)
        sim = DestinationFloodSimulator(
            [Node(node_id, node_id * 10.0, 0.0) for node_id in range(4)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=max_hops, independent_random_streams=True,
        )
        sim.metrics.register_flow(1, 0, 3, 0.0)
        for relay, delay, path, marker, request_id in (
            (1, 0.0, (0, 1), None, 1),
            (2, second_delay, second_path, second_marker, second_request_id),
        ):
            sim.transmit_later(
                relay,
                Packet(
                    kind="FLOOD", flow_id=1, origin=0, final_dst=3,
                    ttl=3, created_at=0.0, protocol=protocol.name,
                    request_id=request_id, path=path, repair_index=marker,
                ),
                delay_s=delay,
            )
        metrics = sim.run(2.0)
        return sim, metrics

    def test_decoded_alternate_first_hop_sends_one_extra_ack(self) -> None:
        sim, metrics = self.run_receipts("meshecho-bar-alternate")

        destination_acks = [
            tx for tx in sim.tx_history
            if tx.sender == 3 and tx.packet.kind == "ACK"
        ]
        self.assertEqual([tx.packet.path for tx in destination_acks],
                         [(0, 1, 3), (0, 2, 3)])
        self.assertLessEqual(destination_acks[1].start - destination_acks[0].start, 1.0)
        extra_events = [
            event for event in sim.protocol.action_events
            if event["event"] == "bar_extra_ack_tx"
        ]
        self.assertEqual(
            [(event["flow_id"], event["time"], event["path"], event["mode"])
             for event in extra_events],
            [(1, destination_acks[1].start, (0, 2, 3), "alternate")],
        )
        first_floods = [
            event for event in sim.protocol.action_events
            if event["event"] == "bar_first_flood_rx"
        ]
        candidates = [
            event for event in sim.protocol.action_events
            if event["event"] == "bar_candidate"
        ]
        self.assertEqual(
            [(event["flow_id"], event["path"]) for event in first_floods],
            [(1, (0, 1, 3))],
        )
        self.assertEqual(
            [(event["flow_id"], event["first_path"],
              event["alternate_path"], event["reply_path"])
             for event in candidates],
            [(1, (0, 1, 3), (0, 2, 3), (0, 2, 3))],
        )
        self.assertEqual(metrics.unicast_deliveries, 1)
        self.assertEqual(metrics.duplicate_rx, 1)

    def test_invalid_duplicate_paths_do_not_add_acks_beyond_fixed_f(self) -> None:
        cases = (
            ("forged last hop", (0, 4), None, 1, 4),
            ("loop", (0, 2, 0, 2), None, 1, 4),
            ("too many hops", (0, 4, 5, 2), None, 1, 3),
            ("different repair marker", (0, 2), 2, 1, 4),
            ("bad request alias", (0, 2), None, 999, 4),
        )
        for label, path, marker, request_id, max_hops in cases:
            with self.subTest(label=label):
                candidate, _ = self.run_receipts(
                    "meshecho-bar-alternate", path, marker, request_id, max_hops,
                )
                fixed, _ = self.run_receipts(
                    "meshecho-dhr-flood", path, marker, request_id, max_hops,
                )
                self.assertEqual(candidate.metrics.ack_tx, fixed.metrics.ack_tx)

    def test_duplicate_decoded_exactly_at_one_second_is_eligible(self) -> None:
        sim, _ = self.run_receipts(
            "meshecho-bar-alternate", second_delay=1.0,
        )

        destination_acks = [
            tx for tx in sim.tx_history
            if tx.sender == 3 and tx.packet.kind == "ACK"
        ]
        self.assertEqual([tx.packet.path for tx in destination_acks],
                         [(0, 1, 3), (0, 2, 3)])
        first = next(
            event for event in sim.protocol.action_events
            if event["event"] == "bar_first_flood_rx"
        )
        candidate = next(
            event for event in sim.protocol.action_events
            if event["event"] == "bar_candidate"
        )
        self.assertEqual(candidate["time"] - first["time"], 1.0)

    def test_first_eligible_alternate_wins_only_one_extra_ack(self) -> None:
        protocol = build_protocol("meshecho-bar-alternate")
        sim = DestinationFloodSimulator(
            [Node(node_id, node_id * 10.0, 0.0) for node_id in range(4)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=4, independent_random_streams=True,
        )
        sim.metrics.register_flow(1, 0, 3, 0.0)
        for sender, delay, path in (
            (1, 0.0, (0, 1)),
            (1, 0.3, (0, 2, 1)),
            (2, 0.6, (0, 2)),
            (2, 0.9, (0, 2)),
        ):
            sim.transmit_later(
                sender,
                Packet(
                    kind="FLOOD", flow_id=1, origin=0, final_dst=3,
                    ttl=3, created_at=0.0, protocol=protocol.name,
                    request_id=1, path=path,
                ),
                delay_s=delay,
            )

        sim.run(2.0)

        destination_acks = [
            tx.packet.path for tx in sim.tx_history
            if tx.sender == 3 and tx.packet.kind == "ACK"
        ]
        self.assertEqual(destination_acks, [(0, 1, 3), (0, 2, 3)])
        self.assertEqual(
            sum(event["event"] == "bar_candidate"
                for event in protocol.action_events), 1,
        )
        self.assertEqual(
            sum(event["event"] == "bar_extra_ack_tx"
                for event in protocol.action_events), 1,
        )

    def test_full_window_capacity_declines_ninth_without_evicting_first(self) -> None:
        protocol = build_protocol("meshecho-bar-alternate")
        sim = DestinationFloodSimulator(
            [Node(node_id, node_id * 10.0, 0.0) for node_id in range(4)],
            RadioConfig(sf=7, bw_hz=500_000, payload_bytes=1,
                        shadow_sigma_db=0.0),
            protocol, seed=17, max_hops=4, independent_random_streams=True,
        )

        def send(flow_id, relay, delay):
            sim.transmit_later(
                relay,
                Packet(
                    kind="FLOOD", flow_id=flow_id, origin=0, final_dst=3,
                    ttl=3, created_at=-100.0, protocol=protocol.name,
                    request_id=flow_id, path=(0, relay),
                ),
                delay_s=delay,
            )

        for flow_id in range(1, 11):
            sim.metrics.register_flow(flow_id, 0, 3, 0.0)
        for flow_id in range(1, 10):
            send(flow_id, 1, (flow_id - 1) * 0.05)
        send(9, 2, 0.51)
        send(1, 2, 0.60)
        send(10, 1, 1.20)
        send(10, 2, 1.30)

        sim.run(2.0)

        destination_acks = [
            tx.packet.flow_id for tx in sim.tx_history
            if tx.sender == 3 and tx.packet.kind == "ACK"
        ]
        self.assertEqual(destination_acks.count(1), 2)
        self.assertEqual(destination_acks.count(9), 1)
        self.assertEqual(destination_acks.count(10), 2)

    def test_busy_destination_cancels_extra_ack_that_cannot_start_in_window(self) -> None:
        protocol = build_protocol("meshecho-bar-alternate")
        sim = DestinationFloodSimulator(
            [Node(node_id, node_id * 10.0, 0.0) for node_id in range(4)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=4, independent_random_streams=True,
        )
        sim.metrics.register_flow(1, 0, 3, 0.0)
        for relay, delay in ((1, 0.0), (2, 0.3)):
            sim.transmit_later(
                relay,
                Packet(
                    kind="FLOOD", flow_id=1, origin=0, final_dst=3,
                    ttl=3, created_at=-100.0, protocol=protocol.name,
                    request_id=1, path=(0, relay),
                ),
                delay_s=delay,
            )
        sim.schedule(
            0.25, "protocol_timer",
            lambda: setattr(sim.nodes[3], "tx_available_at", 2.0),
        )

        sim.run(2.1)

        destination_acks = [
            tx for tx in sim.tx_history
            if tx.sender == 3 and tx.packet.kind == "ACK"
        ]
        self.assertEqual(len(destination_acks), 1)
        self.assertEqual(
            sum(event["event"] == "bar_candidate"
                for event in protocol.action_events), 1,
        )
        self.assertFalse(any(
            event["event"] == "bar_extra_ack_tx"
            for event in protocol.action_events
        ))

    def test_routed_delivery_then_flood_uses_first_flood_ack_as_reference(self) -> None:
        for name, expected_extra_path in (
            ("meshecho-bar-alternate", (0, 1, 3)),
            ("meshecho-bar-same", (0, 2, 3)),
            ("meshecho-dhr-flood", None),
        ):
            with self.subTest(protocol=name):
                protocol = build_protocol(name)
                sim = DestinationFloodSimulator(
                    [Node(node_id, node_id * 10.0, 0.0) for node_id in range(4)],
                    RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
                    seed=17, max_hops=4, independent_random_streams=True,
                )
                sim.metrics.register_flow(1, 0, 3, 0.0)
                sim.transmit_later(
                    1,
                    Packet(
                        kind="DATA", flow_id=1, origin=0, final_dst=3,
                        ttl=3, created_at=0.0, protocol=protocol.name,
                        request_id=1, path=(0, 1, 3), path_index=1,
                    ),
                    delay_s=0.0,
                )
                for relay, delay in ((2, 0.3), (1, 0.6)):
                    sim.transmit_later(
                        relay,
                        Packet(
                            kind="FLOOD", flow_id=1, origin=0, final_dst=3,
                            ttl=3, created_at=0.0, protocol=protocol.name,
                            request_id=1, path=(0, relay), repair_index=2,
                        ),
                        delay_s=delay,
                    )

                metrics = sim.run(2.0)

                destination_acks = [
                    tx.packet for tx in sim.tx_history
                    if tx.sender == 3 and tx.packet.kind == "ACK"
                ]
                expected = [(0, 1, 3), (0, 2, 3)]
                if expected_extra_path is not None:
                    expected.append(expected_extra_path)
                self.assertEqual([packet.path for packet in destination_acks], expected)
                self.assertEqual(metrics.unicast_deliveries, 1)
                if expected_extra_path is not None:
                    self.assertEqual(destination_acks[-1].repair_index, 2)

    def test_alternate_recovery_ack_can_close_routed_flow_at_source(self) -> None:
        class TwoPathRecoverySimulator(Simulator):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.first_recovery_path = None
                self.tx_history = []

            def begin_transmission(self, sender, packet, pending):
                before = self.metrics.tx_count
                super().begin_transmission(sender, packet, pending)
                if self.metrics.tx_count > before:
                    self.tx_history.append(self.transmissions[-1])

            def transmit_later(self, sender, packet, delay_s, pending=None):
                if (sender == 2 and packet.flow_id == 2
                        and packet.kind == "FLOOD" and packet.repair_index == 2):
                    delay_s += 0.25
                return super().transmit_later(sender, packet, delay_s, pending)

            def try_receive(self, tx, receiver):
                packet = tx.packet
                edge = (tx.sender, receiver)
                route_edges = {(0, 1), (1, 3), (3, 1), (1, 0)}
                recovery_edges = route_edges | {
                    (0, 2), (2, 3), (3, 2), (2, 0),
                }
                allowed = route_edges if (packet.flow_id == 1 or
                                          packet.kind == "DATA") else recovery_edges
                if edge not in allowed:
                    return None
                if (packet.flow_id == 2 and packet.kind == "ACK"
                        and (packet.repair_index is None or
                             packet.path == self.first_recovery_path)):
                    return None
                rx = super().try_receive(tx, receiver)
                if (rx is not None and packet.flow_id == 2
                        and packet.kind == "FLOOD" and packet.repair_index == 2
                        and receiver == 3 and self.first_recovery_path is None):
                    self.first_recovery_path = packet.path + (receiver,)
                return rx

        protocol = build_protocol("meshecho-bar-alternate")
        sim = TwoPathRecoverySimulator(
            [Node(node_id, node_id * 10.0, 0.0) for node_id in range(4)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=4, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 3, 1))
        sim.schedule(3.0, "app_send", (0, 3, 2))

        metrics = sim.run(34.0)

        extra = [
            event for event in protocol.action_events
            if event["event"] == "bar_extra_ack_tx" and event["flow_id"] == 2
        ]
        self.assertEqual(protocol.flow_data_actions[2], "R")
        self.assertEqual(
            len(extra), 1,
            msg=(sim.first_recovery_path,
                 [event for event in protocol.action_events
                  if event.get("flow_id") == 2],
                 [(tx.sender, tx.start, tx.packet.path)
                  for tx in sim.tx_history
                  if tx.packet.flow_id == 2 and tx.packet.kind == "FLOOD"]),
        )
        self.assertIsNotNone(metrics.flows[2].acked_at)
        self.assertLessEqual(metrics.flows[2].acked_at, 33.0)
        self.assertEqual(protocol.route_cache[0][3].path, extra[0]["path"])
        self.assertNotEqual(sim.first_recovery_path, extra[0]["path"])


if __name__ == "__main__":
    unittest.main()
