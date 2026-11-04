import unittest
from dataclasses import replace
from types import SimpleNamespace

from lora_mesh_sim import Node, Packet, RadioConfig, Simulator, build_protocol


class TraceSimulator(Simulator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tx_history = []

    def begin_transmission(self, sender, packet, pending):
        before = self.metrics.tx_count
        super().begin_transmission(sender, packet, pending)
        if self.metrics.tx_count > before:
            self.tx_history.append(self.transmissions[-1])


def direct_flow(protocol_name):
    sim = TraceSimulator(
        [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
        RadioConfig(sf=7, shadow_sigma_db=0.0),
        build_protocol(protocol_name), seed=17, max_hops=6,
        independent_random_streams=True,
    )
    sim.schedule(1.0, "app_send", (0, 1, 1))
    metrics = sim.run(6.0)
    return sim, metrics


class DelayedAckRepeatControlTest(unittest.TestCase):
    def test_first_ack_is_delayed_two_seconds_and_repeat_follows_actual_tx_end(self):
        sim, metrics = direct_flow("meshecho-dhr-flood-ack-delay-repeat")

        acks = [tx for tx in sim.tx_history if tx.packet.kind == "ACK"]
        self.assertEqual(len(acks), 2)
        self.assertAlmostEqual(acks[0].start - metrics.flows[1].delivered_at, 2.0)
        self.assertAlmostEqual(acks[1].start - acks[0].end, 0.5)
        self.assertEqual(acks[1].packet.path, acks[0].packet.path)
        self.assertEqual(
            acks[1].packet.wire_size_bytes(sim.radio.payload_bytes),
            acks[0].packet.wire_size_bytes(sim.radio.payload_bytes),
        )
        self.assertEqual(metrics.ack_tx, 2)

    def test_destination_queue_shifts_both_acks_from_actual_first_tx(self):
        sim = TraceSimulator(
            [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0),
            build_protocol("meshecho-dhr-flood-ack-delay-repeat"),
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.nodes[1].tx_available_at = 5.0
        sim.schedule(1.0, "app_send", (0, 1, 1))

        metrics = sim.run(7.0)

        acks = [tx for tx in sim.tx_history if tx.packet.kind == "ACK"]
        self.assertEqual(len(acks), 2)
        self.assertAlmostEqual(acks[0].start, 5.0)
        self.assertGreater(acks[0].start - metrics.flows[1].delivered_at, 2.0)
        self.assertAlmostEqual(acks[1].start - acks[0].end, 0.5)

    def test_queued_repeat_beyond_local_window_is_not_transmitted_or_charged(self):
        sim = TraceSimulator(
            [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0),
            build_protocol("meshecho-dhr-flood-ack-delay-repeat"),
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 1, 1))
        sim.schedule(
            3.3, "protocol_timer",
            lambda: setattr(sim.nodes[1], "tx_available_at", 12.0),
        )

        metrics = sim.run(13.0)

        acks = [tx for tx in sim.tx_history if tx.packet.kind == "ACK"]
        self.assertEqual(len(acks), 1)
        self.assertEqual(metrics.ack_tx, 1)
        self.assertTrue(any(
            event["event"] == "delayed_ack_repeat_drop"
            and event["reason"] == "local-window"
            and event["flow_id"] == 1
            for event in sim.protocol.action_events
        ))

    def test_duplicate_destination_flood_does_not_create_third_ack(self):
        sim = TraceSimulator(
            [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0),
            build_protocol("meshecho-dhr-flood-ack-delay-repeat"),
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 1, 1))
        sim.schedule(
            1.5, "protocol_timer",
            lambda: sim.transmit_later(
                0, sim.tx_history[0].packet, delay_s=0.0,
            ),
        )

        metrics = sim.run(6.0)

        self.assertGreaterEqual(metrics.duplicate_rx, 1)
        self.assertEqual(
            sum(tx.packet.kind == "ACK" for tx in sim.tx_history), 2,
        )

    def test_routed_data_ack_is_immediate_and_not_repeated(self):
        sim = TraceSimulator(
            [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0),
            build_protocol("meshecho-dhr-flood-ack-delay-repeat"),
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 1, 1))
        sim.schedule(5.0, "app_send", (0, 1, 2))

        metrics = sim.run(7.0)

        self.assertEqual(sim.protocol.flow_data_actions[2], "R")
        data_acks = [
            tx for tx in sim.tx_history
            if tx.packet.kind == "ACK" and tx.packet.flow_id == 2
        ]
        self.assertEqual(len(data_acks), 1)
        self.assertAlmostEqual(data_acks[0].start, metrics.flows[2].delivered_at)

    def test_same_flow_data_ack_during_flood_wait_does_not_arm_repeat(self):
        sim = TraceSimulator(
            [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0),
            build_protocol("meshecho-dhr-flood-ack-delay-repeat"),
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 1, 1))
        data = Packet(
            kind="DATA", flow_id=1, origin=0, final_dst=1,
            ttl=sim.max_hops, created_at=1.0, protocol=sim.protocol.name,
            request_id=1, path=(0, 1), path_index=0,
        )
        sim.schedule(
            1.5, "protocol_timer",
            lambda: sim.transmit_later(0, data, delay_s=0.0),
        )

        metrics = sim.run(6.0)

        acks = [
            tx for tx in sim.tx_history
            if tx.sender == 1 and tx.packet.kind == "ACK"
        ]
        self.assertEqual(len(acks), 3)
        flood_ack_start = metrics.flows[1].delivered_at + 2.0
        self.assertLess(acks[0].start, flood_ack_start)
        self.assertAlmostEqual(acks[1].start, flood_ack_start)
        self.assertAlmostEqual(acks[2].start - acks[1].end, 0.5)

    def test_original_delayed_ack_arm_is_unchanged(self):
        original, original_metrics = direct_flow("meshecho-dhr-flood-ack-delay")
        repeat, repeat_metrics = direct_flow(
            "meshecho-dhr-flood-ack-delay-repeat"
        )
        original_ack = next(
            tx for tx in original.tx_history if tx.packet.kind == "ACK"
        )
        first_ack = next(
            tx for tx in repeat.tx_history if tx.packet.kind == "ACK"
        )

        self.assertEqual(original.protocol.flow_data_actions[1], "F")
        self.assertEqual(repeat.protocol.flow_data_actions[1], "F")
        self.assertAlmostEqual(original_ack.start, first_ack.start)
        self.assertEqual(
            replace(first_ack.packet, protocol=original_ack.packet.protocol),
            original_ack.packet,
        )
        self.assertEqual(original_metrics.ack_tx, 1)
        self.assertEqual(repeat_metrics.ack_tx, 2)

    def test_multihop_repeat_uses_the_same_reverse_path(self):
        class LineSimulator(TraceSimulator):
            def try_receive(self, tx, receiver):
                if abs(tx.sender - receiver) != 1:
                    return None
                return super().try_receive(tx, receiver)

        sim = LineSimulator(
            [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0),
             Node(2, 20.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0),
            build_protocol("meshecho-dhr-flood-ack-delay-repeat"),
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 2, 1))

        sim.run(8.0)

        acks = [tx for tx in sim.tx_history if tx.packet.kind == "ACK"]
        destination_acks = [tx for tx in acks if tx.sender == 2]
        self.assertEqual(len(destination_acks), 2)
        self.assertEqual(len([tx for tx in acks if tx.sender == 1]), 2)
        self.assertTrue(all(tx.packet.path == (0, 1, 2) for tx in acks))
        self.assertAlmostEqual(
            destination_acks[1].start - destination_acks[0].end, 0.5,
        )

    def test_ninth_overlapping_flow_gets_first_ack_but_no_repeat(self):
        destination = 9
        nodes = [Node(i, 0.0, 0.0, role="client") for i in range(9)]
        nodes.append(Node(destination, 10.0, 0.0, role="client"))
        sim = TraceSimulator(
            nodes, RadioConfig(sf=7, shadow_sigma_db=0.0),
            build_protocol("meshecho-dhr-flood-ack-delay-repeat"),
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.nodes[destination].tx_available_at = 5.0
        for src in range(9):
            sim.schedule(1.0 + 0.3 * src, "app_send", (src, destination, src + 1))

        metrics = sim.run(9.0)

        destination_acks = [
            tx for tx in sim.tx_history
            if tx.sender == destination and tx.packet.kind == "ACK"
        ]
        self.assertEqual(len(destination_acks), 17)
        self.assertEqual(
            {flow: sum(tx.packet.flow_id == flow for tx in destination_acks)
             for flow in range(1, 10)},
            {**{flow: 2 for flow in range(1, 9)}, 9: 1},
        )
        self.assertEqual(metrics.ack_tx, 17)
        self.assertTrue(any(
            event["event"] == "delayed_ack_repeat_drop"
            and event["reason"] == "active-capacity"
            and event["flow_id"] == 9
            for event in sim.protocol.action_events
        ))

    def test_expiry_reclaims_record_before_a_later_flow(self):
        sim = TraceSimulator(
            [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0),
            build_protocol("meshecho-dhr-flood-ack-delay-repeat"),
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.nodes[1].tx_available_at = 15.0
        sim.schedule(1.0, "app_send", (0, 1, 1))
        sim.schedule(12.0, "app_send", (0, 1, 2))

        sim.run(18.0)

        destination_acks = [
            tx for tx in sim.tx_history
            if tx.sender == 1 and tx.packet.kind == "ACK"
        ]
        self.assertEqual(
            {flow: sum(tx.packet.flow_id == flow for tx in destination_acks)
             for flow in (1, 2)},
            {1: 1, 2: 2},
        )

    def test_local_repeat_can_transmit_after_source_deadline_without_acceptance(self):
        sim = TraceSimulator(
            [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0),
            build_protocol(
                "meshecho-dhr-flood-ack-delay-repeat",
                SimpleNamespace(sr_app_deadline_s=1.0),
            ),
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 1, 1))

        metrics = sim.run(6.0)

        self.assertEqual(metrics.ack_tx, 2)
        self.assertIsNone(metrics.flows[1].acked_at)

    def test_marked_recovery_flood_repeats_same_ack_marker_and_wire_size(self):
        class DropInitialData(TraceSimulator):
            def try_receive(self, tx, receiver):
                if (tx.packet.kind == "DATA" and tx.packet.flow_id == 2
                        and tx.packet.repair_index is None):
                    self.metrics.rx_fail += 1
                    return None
                return super().try_receive(tx, receiver)

        sim = DropInitialData(
            [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0),
            build_protocol("meshecho-dhr-flood-ack-delay-repeat"),
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 1, 1))
        sim.schedule(200.0, "app_send", (0, 1, 2))

        metrics = sim.run(231.0)

        self.assertEqual(sim.protocol.flow_data_actions[2], "R")
        acks = [
            tx for tx in sim.tx_history
            if tx.sender == 1 and tx.packet.kind == "ACK"
            and tx.packet.flow_id == 2
        ]
        self.assertEqual(len(acks), 2)
        self.assertTrue(all(tx.packet.repair_index == 2 for tx in acks))
        self.assertTrue(all(tx.packet.path == (0, 1) for tx in acks))
        self.assertAlmostEqual(acks[0].start - metrics.flows[2].delivered_at, 2.0)
        self.assertAlmostEqual(acks[1].start - acks[0].end, 0.5)
        self.assertEqual(
            acks[0].packet.wire_size_bytes(sim.radio.payload_bytes),
            acks[1].packet.wire_size_bytes(sim.radio.payload_bytes),
        )


if __name__ == "__main__":
    unittest.main()
