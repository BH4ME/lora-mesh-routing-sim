import unittest
from dataclasses import replace

from lora_mesh_sim import Node, RadioConfig, Simulator, build_protocol, required_snr_db


class ControlledLPRSimulator(Simulator):
    def __init__(self, *args, weak_hop=2, **kwargs):
        super().__init__(*args, **kwargs)
        self.weak_hop = weak_hop
        self.sent = []

    def begin_transmission(self, sender, packet, pending):
        before = self.metrics.tx_count
        super().begin_transmission(sender, packet, pending)
        if self.metrics.tx_count > before:
            self.sent.append((sender, packet))

    def try_receive(self, tx, receiver):
        if tx.sender == 0 and receiver in {2, 3}:
            return None
        if tx.sender == 1 and receiver == 3:
            return None
        rx = super().try_receive(tx, receiver)
        if rx is None or tx.packet.kind not in {"DATA", "FLOOD", "PATCH", "PATCH_RELAY"}:
            return rx
        margin_db = 2.0 if tx.packet.flow_id == 2 and tx.sender == self.weak_hop - 1 else 10.0
        return replace(rx, snr_db=required_snr_db(self.radio.sf) + margin_db)


def run_three_flows(protocol_name, *, weak_hop=2, third_at=40.0, seed=17):
    protocol = build_protocol(protocol_name)
    sim = ControlledLPRSimulator(
        [Node(0, 0.0, 0.0), Node(1, 100.0, 0.0),
         Node(2, 200.0, 0.0), Node(3, 300.0, 0.0)],
        RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
        seed=seed, max_hops=6, independent_random_streams=True,
        weak_hop=weak_hop,
    )
    for flow_id, when in enumerate((1.0, 20.0, third_at), start=1):
        sim.schedule(when, "app_send", (0, 3, flow_id))
    metrics = sim.run(third_at + 40.0)
    return sim, protocol, metrics


class MeshEchoLPRControlTest(unittest.TestCase):
    def test_all_controls_pay_the_same_data_and_ack_feedback_bytes(self):
        baseline, _, _ = run_three_flows("meshecho-lpr")

        def first_two_wire_frames(sim):
            return [
                (sender, packet.kind, packet.wire_size_bytes(sim.radio.payload_bytes))
                for sender, packet in sim.sent
                if packet.flow_id in {1, 2} and packet.kind in {"DATA", "FLOOD", "ACK"}
            ]

        expected = first_two_wire_frames(baseline)
        self.assertTrue(any(kind == "ACK" for _, kind, _ in expected))
        for name in (
            "meshecho-lpr-fr",
            "meshecho-lpr-trigger-f",
            "meshecho-lpr-periodic",
            "meshecho-lpr-unobserved-edge",
        ):
            with self.subTest(protocol=name):
                sim, protocol, _ = run_three_flows(name)
                self.assertEqual(protocol.name, name)
                self.assertEqual(first_two_wire_frames(sim), expected)

    def test_fr_only_keeps_feedback_bytes_but_never_repairs_risky_route(self):
        lpr, lpr_protocol, _ = run_three_flows("meshecho-lpr")
        fr, fr_protocol, metrics = run_three_flows("meshecho-lpr-fr")

        self.assertEqual(lpr_protocol.flow_actions[3], "P")
        self.assertEqual(fr_protocol.flow_actions[3], "R")
        self.assertIsNotNone(metrics.flows[3].acked_at)
        self.assertFalse(any(
            packet.kind in {"PATCH", "PATCH_RELAY"} and packet.flow_id == 3
            for _, packet in fr.sent
        ))
        self.assertEqual(
            [(packet.kind, packet.wire_size_bytes(fr.radio.payload_bytes))
             for sender, packet in fr.sent if sender == 0 and packet.flow_id in {1, 2}],
            [(packet.kind, packet.wire_size_bytes(lpr.radio.payload_bytes))
             for sender, packet in lpr.sent if sender == 0 and packet.flow_id in {1, 2}],
        )

    def test_same_trigger_f_spends_repair_budget_on_useful_flood(self):
        _, lpr_protocol, _ = run_three_flows("meshecho-lpr")
        sim, protocol, metrics = run_three_flows("meshecho-lpr-trigger-f")

        self.assertEqual(lpr_protocol.flow_actions[3], "P")
        self.assertEqual(protocol.flow_actions[3], "F")
        self.assertEqual(protocol.source_tokens[0], 0)
        self.assertEqual(protocol.destination_state[(0, 3)].last_repair_at, 40.0)
        self.assertIsNotNone(metrics.flows[3].acked_at)
        source_packets = [packet for sender, packet in sim.sent
                          if sender == 0 and packet.flow_id == 3]
        self.assertEqual(len(source_packets), 1)
        self.assertEqual(source_packets[0].kind, "FLOOD")
        self.assertIsNone(source_packets[0].repair_index)
        self.assertIsNotNone(source_packets[0].min_forward_margin_q)
        self.assertIsNotNone(source_packets[0].min_forward_margin_hop)
        self.assertFalse(any(
            packet.kind in {"PATCH", "PATCH_RELAY"} and packet.flow_id == 3
            for _, packet in sim.sent
        ))

    def test_periodic_repairs_aged_healthy_route_at_ack_indexed_edge(self):
        _, lpr_protocol, _ = run_three_flows(
            "meshecho-lpr", weak_hop=0, third_at=200.0,
        )
        sim, protocol, metrics = run_three_flows(
            "meshecho-lpr-periodic", weak_hop=0, third_at=200.0,
        )

        self.assertEqual(lpr_protocol.flow_actions[3], "R")
        self.assertEqual(protocol.flow_actions[3], "P")
        self.assertEqual(protocol.source_tokens[0], 0)
        self.assertIsNotNone(metrics.flows[3].acked_at)
        source_packets = [packet for sender, packet in sim.sent
                          if sender == 0 and packet.flow_id == 3]
        self.assertEqual(len(source_packets), 1)
        self.assertEqual(source_packets[0].kind, "PATCH")
        self.assertEqual(source_packets[0].repair_index, 1)
        self.assertEqual(
            source_packets[0].wire_size_bytes(sim.radio.payload_bytes),
            replace(source_packets[0], repair_index=None).wire_size_bytes(
                sim.radio.payload_bytes
            ) + 1,
        )

    def test_periodic_does_not_repair_young_risky_route(self):
        _, lpr_protocol, _ = run_three_flows("meshecho-lpr")
        sim, protocol, _ = run_three_flows("meshecho-lpr-periodic")

        self.assertEqual(lpr_protocol.flow_actions[3], "P")
        self.assertEqual(protocol.flow_actions[3], "R")
        self.assertFalse(any(
            packet.kind in {"PATCH", "PATCH_RELAY"} and packet.flow_id == 3
            for _, packet in sim.sent
        ))

    def test_unobserved_edge_keeps_trigger_but_ignores_ack_weak_hop(self):
        lpr, lpr_protocol, _ = run_three_flows("meshecho-lpr", weak_hop=1)
        first, first_protocol, _ = run_three_flows(
            "meshecho-lpr-unobserved-edge", weak_hop=1,
        )
        second, second_protocol, _ = run_three_flows(
            "meshecho-lpr-unobserved-edge", weak_hop=3,
        )

        self.assertEqual(lpr_protocol.flow_actions[3], "P")
        self.assertEqual(first_protocol.flow_actions[3], "P")
        self.assertEqual(second_protocol.flow_actions[3], "P")
        self.assertEqual(first_protocol.source_tokens[0], 0)
        self.assertEqual(second_protocol.source_tokens[0], 0)

        def source_repair_packet(sim):
            return next(packet for sender, packet in sim.sent
                        if sender == 0 and packet.flow_id == 3)

        self.assertEqual(source_repair_packet(lpr).repair_index, 1)
        first_index = source_repair_packet(first).repair_index
        second_index = source_repair_packet(second).repair_index
        self.assertEqual(first_index, second_index)
        self.assertIn(first_index, {1, 2, 3})
        self.assertEqual(
            source_repair_packet(first).wire_size_bytes(first.radio.payload_bytes),
            source_repair_packet(lpr).wire_size_bytes(lpr.radio.payload_bytes),
        )
