import unittest
from dataclasses import replace

from lora_mesh_sim import MeshEchoLPR, Node, RadioConfig, Simulator, build_protocol, required_snr_db


class MeshEchoLPRFeedbackTest(unittest.TestCase):
    def test_ack_reports_weakest_successful_hop_and_pays_for_its_index(self) -> None:
        class MeasuredSimulator(Simulator):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.source_acks = []

            def try_receive(self, tx, receiver):
                if tx.sender == 0 and receiver == 2:
                    return None
                rx = super().try_receive(tx, receiver)
                if rx is None:
                    return None
                if tx.packet.kind in {"DATA", "FLOOD"}:
                    margin_db = 8.0 if tx.sender == 0 else 2.0
                    rx = replace(rx, snr_db=required_snr_db(self.radio.sf) + margin_db)
                if (tx.packet.kind == "ACK" and receiver == tx.packet.final_dst
                        and self.protocol.ack_next_hop_matches(receiver, tx.packet)):
                    self.source_acks.append(tx.packet)
                return rx

        protocol = build_protocol("meshecho-lpr")
        sim = MeasuredSimulator(
            [Node(0, 0.0, 0.0), Node(1, 100.0, 0.0), Node(2, 200.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 2, 1))

        metrics = sim.run(20.0)

        self.assertIsNotNone(metrics.flows[1].acked_at)
        self.assertEqual(len(sim.source_acks), 1)
        ack = sim.source_acks[0]
        self.assertEqual(ack.path, (0, 1, 2))
        self.assertEqual((ack.min_forward_margin_q, ack.min_forward_margin_hop), (4, 2))
        self.assertEqual(
            ack.wire_size_bytes(32),
            replace(ack, min_forward_margin_hop=None).wire_size_bytes(32) + 1,
        )

    def test_risky_confirmed_edge_sends_useful_local_repair_without_rreq(self) -> None:
        class CaptureSimulator(Simulator):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.sent = []

            def begin_transmission(self, sender, packet, pending):
                self.sent.append((sender, packet))
                return super().begin_transmission(sender, packet, pending)

            def try_receive(self, tx, receiver):
                if tx.sender == 0 and receiver == 2:
                    return None
                rx = super().try_receive(tx, receiver)
                if rx is None or tx.packet.kind not in {"DATA", "FLOOD", "PATCH"}:
                    return rx
                margin_db = 10.0 if tx.packet.flow_id == 1 or tx.sender == 0 else 2.0
                return replace(rx, snr_db=required_snr_db(self.radio.sf) + margin_db)

        protocol = build_protocol("meshecho-lpr")
        sim = CaptureSimulator(
            [Node(0, 0.0, 0.0), Node(1, 100.0, 0.0), Node(2, 200.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        for flow_id, when in enumerate((1.0, 20.0, 40.0), start=1):
            sim.schedule(when, "app_send", (0, 2, flow_id))

        metrics = sim.run(80.0)

        self.assertIsNotNone(metrics.flows[3].acked_at)
        self.assertEqual(
            [event["action"] for event in protocol.action_events
             if event["event"] == "decision"],
            ["F", "R", "P"],
        )
        third_flow = [(sender, packet) for sender, packet in sim.sent
                      if packet.flow_id == 3]
        self.assertFalse(any(packet.kind in {"RREQ", "RREP"}
                             for _, packet in third_flow))
        self.assertTrue(any(
            sender == 1 and packet.kind == "PATCH" and packet.app_payload
            and packet.repair_index == 2
            for sender, packet in third_flow
        ))
        self.assertEqual(protocol.route_cache[0][2].path, (0, 1, 2))

    def test_one_relay_bridges_failed_weak_edge_and_ack_commits_realized_path(self) -> None:
        class DiamondSimulator(Simulator):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.sent = []
                self.suppression_before_repair = None

            def begin_transmission(self, sender, packet, pending):
                if sender == 0 and packet.flow_id == 3 and packet.kind == "DATA":
                    self.suppression_before_repair = self.metrics.suppressed_forwards
                self.sent.append((sender, packet))
                return super().begin_transmission(sender, packet, pending)

            def try_receive(self, tx, receiver):
                packet = tx.packet
                if tx.sender == 0 and receiver in {2, 3, 4}:
                    return None
                if tx.sender == 1 and receiver == 3:
                    return None
                if packet.flow_id <= 2 and receiver == 4 and tx.sender != 2:
                    return None
                if packet.flow_id == 3 and packet.kind == "PATCH" and tx.sender == 1 and receiver == 2:
                    return None
                rx = super().try_receive(tx, receiver)
                if rx is None or packet.kind not in {"DATA", "FLOOD", "PATCH", "PATCH_RELAY"}:
                    return rx
                margin_db = 2.0 if packet.flow_id == 2 and tx.sender == 1 else 10.0
                return replace(rx, snr_db=required_snr_db(self.radio.sf) + margin_db)

        protocol = build_protocol("meshecho-lpr")
        sim = DiamondSimulator(
            [Node(0, 0.0, 0.0), Node(1, 100.0, 0.0),
             Node(2, 200.0, 0.0), Node(3, 300.0, 0.0),
             Node(4, 150.0, 100.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        for flow_id, when in enumerate((1.0, 20.0, 40.0), start=1):
            sim.schedule(when, "app_send", (0, 3, flow_id))

        metrics = sim.run(80.0)

        self.assertIsNotNone(metrics.flows[3].acked_at)
        self.assertTrue(any(
            sender == 4 and packet.kind == "PATCH_RELAY" and packet.app_payload
            and packet.path == (0, 1, 4, 2, 3)
            for sender, packet in sim.sent
        ))
        self.assertEqual(protocol.route_cache[0][3].path, (0, 1, 4, 2, 3))
        self.assertFalse(any(
            packet.kind in {"RREQ", "RREP"} and packet.flow_id == 3
            for _, packet in sim.sent
        ))
        self.assertEqual(metrics.suppressed_forwards, sim.suppression_before_repair)

    def test_direct_patch_success_cancels_overhearing_relay(self) -> None:
        class DirectPatchSimulator(Simulator):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.sent = []
                self.patch_heard_by_relay = False

            def begin_transmission(self, sender, packet, pending):
                before = self.metrics.tx_count
                super().begin_transmission(sender, packet, pending)
                if self.metrics.tx_count > before:
                    self.sent.append((sender, packet))

            def try_receive(self, tx, receiver):
                if tx.sender == 0 and receiver in {2, 3}:
                    return None
                if tx.sender == 1 and receiver == 3 and tx.packet.flow_id < 3:
                    return None
                rx = super().try_receive(tx, receiver)
                if rx is None:
                    return None
                if receiver == 3 and tx.packet.kind == "PATCH":
                    self.patch_heard_by_relay = True
                if tx.packet.kind in {"DATA", "FLOOD", "PATCH", "PATCH_RELAY"}:
                    margin_db = 2.0 if tx.packet.flow_id == 2 and tx.sender == 1 else 10.0
                    return replace(rx, snr_db=required_snr_db(self.radio.sf) + margin_db)
                return rx

        protocol = build_protocol("meshecho-lpr")
        sim = DirectPatchSimulator(
            [Node(0, 0.0, 0.0), Node(1, 100.0, 0.0),
             Node(2, 200.0, 0.0), Node(3, 150.0, 100.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        for flow_id, when in enumerate((1.0, 20.0, 40.0), start=1):
            sim.schedule(when, "app_send", (0, 2, flow_id))

        metrics = sim.run(80.0)

        self.assertEqual(protocol.flow_actions[3], "P", protocol.action_events)
        self.assertTrue(sim.patch_heard_by_relay)
        self.assertIsNotNone(metrics.flows[3].acked_at)
        self.assertFalse(any(
            sender == 3 and packet.kind == "PATCH_RELAY" and packet.flow_id == 3
            for sender, packet in sim.sent
        ))
        self.assertEqual(protocol.pending_patch_relays, {})

    def test_earlier_patch_relay_cancels_later_candidate(self) -> None:
        class OrderedPatchProtocol(MeshEchoLPR):
            def flood_delay(self, receiver=None, rx=None):
                if receiver == 4:
                    return 0.05
                if receiver == 5:
                    return 1.2
                return super().flood_delay(receiver, rx)

        class TwoRelaySimulator(Simulator):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.sent = []
                self.patch_heard_by = set()

            def begin_transmission(self, sender, packet, pending):
                before = self.metrics.tx_count
                super().begin_transmission(sender, packet, pending)
                if self.metrics.tx_count > before:
                    self.sent.append((sender, packet))

            def try_receive(self, tx, receiver):
                packet = tx.packet
                if tx.sender == 0 and receiver in {2, 3, 4, 5}:
                    return None
                if tx.sender == 1 and receiver == 3:
                    return None
                if (receiver in {4, 5} and packet.flow_id < 3
                        and not (tx.sender == 2 and packet.kind == "ACK")):
                    return None
                if (packet.flow_id == 3 and packet.kind == "PATCH"
                        and tx.sender == 1 and receiver == 2):
                    return None
                if (packet.flow_id == 3 and packet.kind == "PATCH_RELAY"
                        and tx.sender == 4 and receiver == 2):
                    return None
                rx = super().try_receive(tx, receiver)
                if rx is None:
                    return None
                if packet.flow_id == 3 and packet.kind == "PATCH" and receiver in {4, 5}:
                    self.patch_heard_by.add(receiver)
                if packet.kind in {"DATA", "FLOOD", "PATCH", "PATCH_RELAY"}:
                    margin_db = 2.0 if packet.flow_id == 2 and tx.sender == 1 else 10.0
                    return replace(rx, snr_db=required_snr_db(self.radio.sf) + margin_db)
                return rx

        protocol = OrderedPatchProtocol()
        sim = TwoRelaySimulator(
            [Node(0, 0.0, 0.0), Node(1, 100.0, 0.0),
             Node(2, 200.0, 0.0), Node(3, 300.0, 0.0),
             Node(4, 150.0, 100.0), Node(5, 160.0, -100.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        for flow_id, when in enumerate((1.0, 20.0, 40.0), start=1):
            sim.schedule(when, "app_send", (0, 3, flow_id))

        sim.run(80.0)

        self.assertEqual(protocol.flow_actions[3], "P", protocol.action_events)
        self.assertEqual(sim.patch_heard_by, {4, 5})
        self.assertTrue(any(
            sender == 4 and packet.kind == "PATCH_RELAY" and packet.flow_id == 3
            for sender, packet in sim.sent
        ))
        self.assertFalse(any(
            sender == 5 and packet.kind == "PATCH_RELAY" and packet.flow_id == 3
            for sender, packet in sim.sent
        ))
        self.assertEqual(protocol.pending_patch_relays, {})

    def test_source_origin_patch_starts_ack_timer_and_lost_ack_keeps_old_route(self) -> None:
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

        self.assertIsNotNone(metrics.flows[3].delivered_at)
        self.assertIsNone(metrics.flows[3].acked_at)
        self.assertEqual(protocol.route_cache[0][1].path, (0, 1))
        self.assertTrue(any(
            event["event"] == "timeout" and event["flow_id"] == 3
            and event["reason"] == "source-ack-timeout"
            for event in protocol.action_events
        ))
