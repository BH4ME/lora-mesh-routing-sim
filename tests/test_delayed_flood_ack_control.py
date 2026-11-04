import unittest
from dataclasses import replace
from types import SimpleNamespace

from lora_mesh_sim import Node, RadioConfig, Simulator, build_protocol
from tools.run_sr_experiment import summarize_windowed_transmissions


class TraceSimulator(Simulator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tx_history = []

    def begin_transmission(self, sender, packet, pending):
        before = self.metrics.tx_count
        super().begin_transmission(sender, packet, pending)
        if self.metrics.tx_count > before:
            self.tx_history.append(self.transmissions[-1])


class InitialDataDropSimulator(TraceSimulator):
    def try_receive(self, tx, receiver):
        if (tx.packet.kind == "DATA" and tx.packet.flow_id == 2
                and tx.packet.repair_index is None):
            self.metrics.rx_fail += 1
            return None
        return super().try_receive(tx, receiver)


def run_direct_flow(protocol_name):
    sim = TraceSimulator(
        [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
        RadioConfig(sf=7, shadow_sigma_db=0.0),
        build_protocol(protocol_name), seed=17, max_hops=6,
        independent_random_streams=True,
    )
    sim.schedule(1.0, "app_send", (0, 1, 1))
    metrics = sim.run(6.0)
    return sim, metrics


class DelayedFloodAckControlTest(unittest.TestCase):
    def test_first_flood_ack_starts_two_seconds_after_destination_decode(self):
        immediate, immediate_metrics = run_direct_flow("meshecho-dhr-flood")
        delayed, delayed_metrics = run_direct_flow(
            "meshecho-dhr-flood-ack-delay"
        )
        immediate_ack = next(
            tx for tx in immediate.tx_history if tx.packet.kind == "ACK"
        )
        delayed_ack = next(
            tx for tx in delayed.tx_history if tx.packet.kind == "ACK"
        )

        self.assertAlmostEqual(
            immediate_ack.start, immediate_metrics.flows[1].delivered_at
        )
        self.assertAlmostEqual(
            delayed_ack.start - delayed_metrics.flows[1].delivered_at, 2.0
        )

    def test_routed_data_ack_remains_immediate(self):
        sim = TraceSimulator(
            [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0),
            build_protocol("meshecho-dhr-flood-ack-delay"),
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 1, 1))
        sim.schedule(5.0, "app_send", (0, 1, 2))

        metrics = sim.run(7.0)

        self.assertEqual(sim.protocol.flow_data_actions[2], "R")
        data_ack = next(
            tx for tx in sim.tx_history
            if tx.packet.kind == "ACK" and tx.packet.flow_id == 2
        )
        self.assertAlmostEqual(data_ack.start, metrics.flows[2].delivered_at)

    def test_repeated_flood_does_not_create_an_extra_or_different_ack(self):
        immediate, _ = run_direct_flow("meshecho-dhr-flood")
        delayed = TraceSimulator(
            [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0),
            build_protocol("meshecho-dhr-flood-ack-delay"),
            seed=17, max_hops=6, independent_random_streams=True,
        )
        delayed.schedule(1.0, "app_send", (0, 1, 1))
        delayed.schedule(
            1.5, "protocol_timer",
            lambda: delayed.transmit_later(
                0, delayed.tx_history[0].packet, delay_s=0.0
            ),
        )

        metrics = delayed.run(6.0)

        immediate_ack = next(
            tx.packet for tx in immediate.tx_history if tx.packet.kind == "ACK"
        )
        delayed_acks = [
            tx.packet for tx in delayed.tx_history
            if tx.sender == 1 and tx.packet.kind == "ACK"
        ]
        self.assertGreaterEqual(metrics.duplicate_rx, 1)
        self.assertEqual(len(delayed_acks), 1)
        self.assertEqual(
            replace(delayed_acks[0], protocol=immediate_ack.protocol),
            immediate_ack,
        )
        self.assertEqual(
            delayed_acks[0].wire_size_bytes(delayed.radio.payload_bytes),
            immediate_ack.wire_size_bytes(immediate.radio.payload_bytes),
        )

    def test_delayed_flood_ack_retains_dhr_initial_ack_accounting(self):
        sim, _ = run_direct_flow("meshecho-dhr-flood-ack-delay")

        summary = summarize_windowed_transmissions(
            sim.tx_history, cutoff_s=6.0, app_payload_bytes=32,
        )

        self.assertEqual(summary["windowed_dhr_initial_ack_tx"], 1)
        self.assertEqual(summary["windowed_dhr_flood_ack_tx"], 0)
        self.assertEqual(summary["windowed_ack_tx"], 1)

    def test_run_cutoff_preserves_a_delayed_ack_for_later_drain(self):
        sim = TraceSimulator(
            [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0),
            build_protocol("meshecho-dhr-flood-ack-delay"),
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(629.0, "app_send", (0, 1, 1))

        sim.run(630.0)

        self.assertFalse(any(tx.packet.kind == "ACK" for tx in sim.tx_history))
        self.assertTrue(any(
            event_type == "tx_request" and data[1].kind == "ACK"
            for _, _, event_type, data in sim.events
        ))
        sim.run(660.0)
        self.assertEqual(
            sum(tx.packet.kind == "ACK" for tx in sim.tx_history), 1,
        )

    def test_late_ack_is_transmitted_but_not_accepted_by_source(self):
        sim = TraceSimulator(
            [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0),
            build_protocol(
                "meshecho-dhr-flood-ack-delay",
                SimpleNamespace(sr_app_deadline_s=1.0),
            ),
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 1, 1))

        metrics = sim.run(6.0)

        acks = [tx for tx in sim.tx_history if tx.packet.kind == "ACK"]
        self.assertEqual(len(acks), 1)
        self.assertGreater(acks[0].start, metrics.flows[1].created_at + 1.0)
        self.assertIsNone(metrics.flows[1].acked_at)
        self.assertGreater(metrics.total_airtime_s, 0.0)

    def test_marked_recovery_flood_ack_keeps_marker_and_delay(self):
        sim = InitialDataDropSimulator(
            [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0),
            build_protocol("meshecho-dhr-flood-ack-delay"),
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 1, 1))
        sim.schedule(200.0, "app_send", (0, 1, 2))

        metrics = sim.run(231.0)

        self.assertEqual(sim.protocol.flow_data_actions[2], "R")
        acks = [
            tx for tx in sim.tx_history
            if tx.packet.kind == "ACK" and tx.packet.flow_id == 2
        ]
        self.assertEqual(len(acks), 1)
        self.assertEqual(acks[0].packet.repair_index, 2)
        self.assertEqual(acks[0].packet.path, (0, 1))
        self.assertAlmostEqual(acks[0].start - metrics.flows[2].delivered_at, 2.0)
        self.assertEqual(acks[0].packet.wire_size_bytes(32), 17)

    def test_fixed_two_hop_useful_flood_caps_initial_and_recovery_f_only(self):
        sim = InitialDataDropSimulator(
            [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0),
            build_protocol("meshecho-dhr-flood-ack-delay-flood2"),
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 1, 1))
        sim.schedule(200.0, "app_send", (0, 1, 2))

        sim.run(231.0)

        initial = next(tx.packet for tx in sim.tx_history
                       if tx.sender == 0 and tx.packet.flow_id == 1
                       and tx.packet.kind == "FLOOD")
        recovery = next(tx.packet for tx in sim.tx_history
                        if tx.sender == 0 and tx.packet.flow_id == 2
                        and tx.packet.kind == "FLOOD"
                        and tx.packet.repair_index == 2)
        self.assertEqual(sim.max_hops, 6)
        self.assertEqual(sim.protocol.discovery_ttl_for(0, 1, 3), 6)
        self.assertEqual(initial.ttl, 2)
        self.assertEqual(recovery.ttl, 2)
        self.assertTrue(initial.app_payload)
        self.assertTrue(recovery.app_payload)
        stock = InitialDataDropSimulator(
            [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0),
            build_protocol("meshecho-dhr-flood-ack-delay"),
            seed=17, max_hops=6, independent_random_streams=True,
        )
        stock.schedule(1.0, "app_send", (0, 1, 1))
        stock.schedule(200.0, "app_send", (0, 1, 2))
        stock.run(231.0)
        self.assertEqual(
            [tx.packet.ttl for tx in stock.tx_history
             if tx.sender == 0 and tx.packet.kind == "FLOOD"],
            [6, 6],
        )

    def test_two_hop_flood_rescue_is_admitted_near_the_deadline(self):
        sim = InitialDataDropSimulator(
            [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0),
            build_protocol(
                "meshecho-dhr-flood-ack-delay-flood2",
                SimpleNamespace(sr_app_deadline_s=20.0),
            ),
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 1, 1))
        sim.schedule(200.0, "app_send", (0, 1, 2))

        metrics = sim.run(221.0)

        self.assertEqual(sim.protocol.flow_data_actions[1], "F")
        self.assertEqual(sim.protocol.flow_data_actions[2], "R")
        self.assertTrue(any(
            event.get("event") == "dhr_guard" and event["flow_id"] == 2
            and event["admitted"] and event["selected_action"] == "F"
            for event in sim.protocol.action_events
        ))
        recovery = next(
            tx.packet for tx in sim.tx_history
            if tx.sender == 0 and tx.packet.flow_id == 2
            and tx.packet.kind == "FLOOD" and tx.packet.repair_index == 2
        )
        self.assertEqual(recovery.ttl, 2)
        self.assertIsNotNone(metrics.flows[2].acked_at)
        self.assertLessEqual(metrics.flows[2].acked_at, 220.0)

    def test_destination_queue_can_delay_ack_beyond_fixed_wait(self):
        sim = TraceSimulator(
            [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0),
            build_protocol("meshecho-dhr-flood-ack-delay"),
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.nodes[1].tx_available_at = 5.0
        sim.schedule(1.0, "app_send", (0, 1, 1))

        metrics = sim.run(6.0)

        ack = next(tx for tx in sim.tx_history if tx.packet.kind == "ACK")
        self.assertAlmostEqual(ack.start, 5.0)
        self.assertGreater(ack.start - metrics.flows[1].delivered_at, 2.0)


if __name__ == "__main__":
    unittest.main()
