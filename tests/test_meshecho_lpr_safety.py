import unittest
from dataclasses import replace

from lora_mesh_sim import Node, RadioConfig, Simulator, build_protocol, required_snr_db


class MeshEchoLPRSafetyTest(unittest.TestCase):
    def test_patch_ack_with_wrong_origin_does_not_confirm_flow(self) -> None:
        class SpoofedAckSimulator(Simulator):
            def begin_transmission(self, sender, packet, pending):
                if packet.kind == "ACK" and packet.flow_id == 3:
                    packet = replace(packet, origin=2)
                return super().begin_transmission(sender, packet, pending)

            def try_receive(self, tx, receiver):
                rx = super().try_receive(tx, receiver)
                if rx is None or tx.packet.kind not in {"DATA", "FLOOD", "PATCH"}:
                    return rx
                margin_db = 10.0 if tx.packet.flow_id == 1 else 2.0
                return replace(rx, snr_db=required_snr_db(self.radio.sf) + margin_db)

        protocol = build_protocol("meshecho-lpr")
        sim = SpoofedAckSimulator(
            [Node(0, 0.0, 0.0), Node(1, 100.0, 0.0), Node(2, 300.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        for flow_id, when in enumerate((1.0, 20.0, 40.0), start=1):
            sim.schedule(when, "app_send", (0, 1, flow_id))

        metrics = sim.run(80.0)

        self.assertEqual(protocol.flow_actions[3], "P")
        self.assertIsNotNone(metrics.flows[3].delivered_at)
        self.assertIsNone(metrics.flows[3].acked_at)

    def test_patch_on_confirmed_route_counts_as_cache_hit(self) -> None:
        class MarginSimulator(Simulator):
            def try_receive(self, tx, receiver):
                rx = super().try_receive(tx, receiver)
                if rx is None or tx.packet.kind not in {"DATA", "FLOOD", "PATCH"}:
                    return rx
                margin_db = 10.0 if tx.packet.flow_id == 1 else 2.0
                return replace(rx, snr_db=required_snr_db(self.radio.sf) + margin_db)

        protocol = build_protocol("meshecho-lpr")
        sim = MarginSimulator(
            [Node(0, 0.0, 0.0), Node(1, 100.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        for flow_id, when in enumerate((1.0, 20.0, 40.0), start=1):
            sim.schedule(when, "app_send", (0, 1, flow_id))

        metrics = sim.run(80.0)

        self.assertEqual([protocol.flow_actions[i] for i in (1, 2, 3)],
                         ["F", "R", "P"])
        self.assertEqual(metrics.route_cache_hits, 2)
        self.assertEqual(metrics.route_cache_misses, 1)

    def test_confirmed_patch_releases_source_repair_index(self) -> None:
        class MarginSimulator(Simulator):
            def try_receive(self, tx, receiver):
                rx = super().try_receive(tx, receiver)
                if rx is None or tx.packet.kind not in {"DATA", "FLOOD", "PATCH"}:
                    return rx
                margin_db = 10.0 if tx.packet.flow_id == 1 else 2.0
                return replace(rx, snr_db=required_snr_db(self.radio.sf) + margin_db)

        protocol = build_protocol("meshecho-lpr")
        sim = MarginSimulator(
            [Node(0, 0.0, 0.0), Node(1, 100.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        for flow_id, when in enumerate((1.0, 20.0, 40.0), start=1):
            sim.schedule(when, "app_send", (0, 1, flow_id))

        metrics = sim.run(45.0)

        self.assertEqual(protocol.flow_actions[3], "P")
        self.assertIsNotNone(metrics.flows[3].acked_at)
        self.assertEqual(protocol.flow_repair_indices, {})

    def test_unconfirmed_patch_releases_source_index_after_deadline(self) -> None:
        class LostAckSimulator(Simulator):
            def try_receive(self, tx, receiver):
                if tx.packet.kind == "ACK" and tx.packet.flow_id == 3 and receiver == 0:
                    return None
                rx = super().try_receive(tx, receiver)
                if rx is None or tx.packet.kind not in {"DATA", "FLOOD", "PATCH"}:
                    return rx
                margin_db = 10.0 if tx.packet.flow_id == 1 else 2.0
                return replace(rx, snr_db=required_snr_db(self.radio.sf) + margin_db)

        protocol = build_protocol("meshecho-lpr")
        sim = LostAckSimulator(
            [Node(0, 0.0, 0.0), Node(1, 100.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        for flow_id, when in enumerate((1.0, 20.0, 40.0), start=1):
            sim.schedule(when, "app_send", (0, 1, flow_id))

        metrics = sim.run(80.0)

        self.assertEqual(protocol.flow_actions[3], "P")
        self.assertIsNone(metrics.flows[3].acked_at)
        self.assertEqual(protocol.flow_repair_indices, {})

    def test_confirmed_patch_keeps_feedback_fresh_for_next_route_use(self) -> None:
        class MarginSimulator(Simulator):
            def try_receive(self, tx, receiver):
                rx = super().try_receive(tx, receiver)
                if rx is None or tx.packet.kind not in {"DATA", "FLOOD", "PATCH"}:
                    return rx
                margin_db = 10.0 if tx.packet.flow_id == 1 else 2.0
                return replace(rx, snr_db=required_snr_db(self.radio.sf) + margin_db)

        protocol = build_protocol("meshecho-lpr")
        sim = MarginSimulator(
            [Node(0, 0.0, 0.0), Node(1, 100.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        for flow_id, when in enumerate((1.0, 20.0, 40.0, 321.0), start=1):
            sim.schedule(when, "app_send", (0, 1, flow_id))

        metrics = sim.run(340.0)

        self.assertIsNotNone(metrics.flows[3].acked_at)
        self.assertLess(321.0 - metrics.flows[3].acked_at, 300.0)
        self.assertEqual(protocol.flow_actions[4], "R")

    def test_patch_ack_just_after_application_deadline_cannot_commit(self) -> None:
        class DelayedAckSimulator(Simulator):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.delayed_ack = None

            def try_receive(self, tx, receiver):
                if tx.packet.kind == "ACK" and tx.packet.flow_id == 3 and receiver == 0:
                    self.delayed_ack = tx.packet
                    return None
                rx = super().try_receive(tx, receiver)
                if rx is None or tx.packet.kind not in {"DATA", "FLOOD", "PATCH"}:
                    return rx
                margin_db = 10.0 if tx.packet.flow_id == 1 else 2.0
                return replace(rx, snr_db=required_snr_db(self.radio.sf) + margin_db)

        protocol = build_protocol("meshecho-lpr")
        sim = DelayedAckSimulator(
            [Node(0, 0.0, 0.0), Node(1, 100.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        for flow_id, when in enumerate((1.0, 20.0, 40.0), start=1):
            sim.schedule(when, "app_send", (0, 1, flow_id))
        sim.schedule(
            70.0000005, "protocol_timer",
            lambda: protocol.on_ack_packet(0, sim.delayed_ack),
        )

        metrics = sim.run(70.0000005)

        self.assertIsNotNone(sim.delayed_ack)
        self.assertEqual(protocol.flow_actions[3], "P")
        self.assertIsNone(metrics.flows[3].acked_at)
        self.assertEqual(protocol.route_cache[0][1].path, (0, 1))
