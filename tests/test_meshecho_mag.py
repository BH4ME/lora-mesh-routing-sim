import unittest
from argparse import Namespace
from dataclasses import replace

from lora_mesh_sim import Node, Packet, RadioConfig, Simulator, build_protocol, required_snr_db


class MeshEchoMAGPacketTest(unittest.TestCase):
    def test_optional_forward_margin_is_charged_and_survives_forwarding(self) -> None:
        base = Packet(
            kind="DATA", flow_id=1, origin=0, final_dst=2, ttl=6,
            created_at=1.0, protocol="meshecho-mag", path=(0, 1, 2),
        )
        zero = Packet(
            kind="DATA", flow_id=1, origin=0, final_dst=2, ttl=6,
            created_at=1.0, protocol="meshecho-mag", path=(0, 1, 2),
            min_forward_margin_q=0,
        )
        negative = Packet(
            kind="DATA", flow_id=1, origin=0, final_dst=2, ttl=6,
            created_at=1.0, protocol="meshecho-mag", path=(0, 1, 2),
            min_forward_margin_q=-6,
        )

        self.assertEqual(zero.wire_size_bytes(32), base.wire_size_bytes(32) + 1)
        self.assertEqual(negative.wire_size_bytes(32), zero.wire_size_bytes(32))
        self.assertEqual(negative.with_ttl(5).min_forward_margin_q, -6)
        self.assertEqual(negative.advance_path().min_forward_margin_q, -6)
        self.assertEqual(negative.retreat_path().min_forward_margin_q, -6)
        self.assertEqual(negative.append_path(3).min_forward_margin_q, -6)


class MeshEchoMAGFeedbackTest(unittest.TestCase):
    def test_two_hop_forward_margin_returns_on_flood_and_route_acks(self) -> None:
        class MeasuredSimulator(Simulator):
            source_ack_margins = None

            def try_receive(self, tx, receiver):
                if tx.sender == 0 and receiver == 2:
                    return None
                rx = super().try_receive(tx, receiver)
                if rx is None:
                    return None
                if tx.packet.kind in {"FLOOD", "DATA"}:
                    margin_db = 8.0 if tx.sender == 0 or tx.packet.flow_id == 1 else 2.0
                    rx = replace(rx, snr_db=required_snr_db(self.radio.sf) + margin_db)
                if (tx.packet.kind == "ACK" and receiver == tx.packet.final_dst
                        and self.protocol.ack_next_hop_matches(receiver, tx.packet)):
                    self.source_ack_margins.append(tx.packet.min_forward_margin_q)
                return rx

        protocol = build_protocol("meshecho-mag")
        sim = MeasuredSimulator(
            [Node(0, 0.0, 0.0), Node(1, 100.0, 0.0), Node(2, 200.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.source_ack_margins = []
        sim.schedule(1.0, "app_send", (0, 2, 1))
        sim.schedule(20.0, "app_send", (0, 2, 2))

        metrics = sim.run(50.0)

        self.assertIsNotNone(metrics.flows[1].acked_at)
        self.assertIsNotNone(metrics.flows[2].acked_at)
        self.assertEqual(sim.source_ack_margins, [16, 4])
        self.assertEqual(
            [event["action"] for event in protocol.action_events
             if event["event"] == "decision"],
            ["F", "R"],
        )

    def test_low_acked_margin_triggers_prefailure_discovery(self) -> None:
        class FallingMarginSimulator(Simulator):
            def try_receive(self, tx, receiver):
                rx = super().try_receive(tx, receiver)
                if rx is None or tx.packet.kind not in {"FLOOD", "DATA"}:
                    return rx
                margin_db = 10.0 if tx.packet.flow_id == 1 else 2.0
                return replace(rx, snr_db=required_snr_db(self.radio.sf) + margin_db)

        protocol = build_protocol("meshecho-mag")
        sim = FallingMarginSimulator(
            [Node(0, 0.0, 0.0), Node(1, 100.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        for flow_id, when in enumerate((1.0, 20.0, 40.0), start=1):
            sim.schedule(when, "app_send", (0, 1, flow_id))

        metrics = sim.run(100.0)

        self.assertIsNotNone(metrics.flows[2].acked_at)
        self.assertEqual(
            [event["action"] for event in protocol.action_events
             if event["event"] == "decision"],
            ["F", "R", "D"],
        )

    def test_missing_ack_does_not_expose_forward_margin_to_source(self) -> None:
        class LostAckSimulator(Simulator):
            def try_receive(self, tx, receiver):
                if tx.packet.kind == "ACK" and tx.packet.flow_id == 2 and receiver == 0:
                    return None
                rx = super().try_receive(tx, receiver)
                if rx is None or tx.packet.kind not in {"FLOOD", "DATA"}:
                    return rx
                margin_db = 10.0 if tx.packet.flow_id == 1 else 1.0
                return replace(rx, snr_db=required_snr_db(self.radio.sf) + margin_db)

        protocol = build_protocol("meshecho-mag")
        sim = LostAckSimulator(
            [Node(0, 0.0, 0.0), Node(1, 100.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        for flow_id, when in enumerate((1.0, 20.0, 40.0), start=1):
            sim.schedule(when, "app_send", (0, 1, flow_id))

        sim.run(40.0)

        self.assertEqual(protocol.destination_state[(0, 1)].acked_margins_q, [20])
        self.assertEqual(
            [event["action"] for event in protocol.action_events
             if event["event"] == "decision"],
            ["F", "R", "R"],
        )

    def test_discovery_that_cannot_meet_deadline_reuses_confirmed_route(self) -> None:
        class SlowRadioSimulator(Simulator):
            def try_receive(self, tx, receiver):
                rx = super().try_receive(tx, receiver)
                if rx is None or tx.packet.kind not in {"FLOOD", "DATA"}:
                    return rx
                margin_db = 10.0 if tx.packet.flow_id == 1 else 2.0
                return replace(rx, snr_db=required_snr_db(self.radio.sf) + margin_db)

        protocol = build_protocol("meshecho-mag")
        sim = SlowRadioSimulator(
            [Node(0, 0.0, 0.0), Node(1, 100.0, 0.0)],
            RadioConfig(sf=12, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
            matched_rreq_timing=True,
        )
        for flow_id, when in enumerate((1.0, 20.0, 40.0), start=1):
            sim.schedule(when, "app_send", (0, 1, flow_id))

        sim.run(40.0)

        self.assertEqual(
            [event["action"] for event in protocol.action_events
             if event["event"] == "decision"],
            ["F", "R", "R"],
        )

    def test_risk_without_repeated_demand_reuses_confirmed_route(self) -> None:
        class LowMarginSimulator(Simulator):
            def try_receive(self, tx, receiver):
                rx = super().try_receive(tx, receiver)
                if rx is None or tx.packet.kind not in {"FLOOD", "DATA"}:
                    return rx
                return replace(rx, snr_db=required_snr_db(self.radio.sf) + 2.0)

        protocol = build_protocol("meshecho-mag")
        sim = LowMarginSimulator(
            [Node(0, 0.0, 0.0), Node(1, 100.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 1, 1))
        sim.schedule(20.0, "app_send", (0, 1, 2))

        sim.run(20.0)

        self.assertEqual(
            [event["action"] for event in protocol.action_events
             if event["event"] == "decision"],
            ["F", "R"],
        )

    def test_matched_controls_change_only_the_risk_action(self) -> None:
        class FallingMarginSimulator(Simulator):
            def try_receive(self, tx, receiver):
                rx = super().try_receive(tx, receiver)
                if rx is None or tx.packet.kind not in {"FLOOD", "DATA"}:
                    return rx
                margin_db = 10.0 if tx.packet.flow_id == 1 else 2.0
                return replace(rx, snr_db=required_snr_db(self.radio.sf) + margin_db)

        expected = {
            "meshecho-mag": "D",
            "meshecho-mag-fr": "R",
            "meshecho-mag-trigger-f": "F",
            "meshecho-mag-periodic": "R",
        }
        for name, third_action in expected.items():
            with self.subTest(name=name):
                protocol = build_protocol(name)
                sim = FallingMarginSimulator(
                    [Node(0, 0.0, 0.0), Node(1, 100.0, 0.0)],
                    RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
                    seed=17, max_hops=6, independent_random_streams=True,
                )
                for flow_id, when in enumerate((1.0, 20.0, 40.0), start=1):
                    sim.schedule(when, "app_send", (0, 1, flow_id))
                sim.run(40.0)
                self.assertEqual(
                    [event["action"] for event in protocol.action_events
                     if event["event"] == "decision"],
                    ["F", "R", third_action],
                )

    def test_periodic_control_discovers_on_healthy_old_route(self) -> None:
        class HealthyMarginSimulator(Simulator):
            def try_receive(self, tx, receiver):
                rx = super().try_receive(tx, receiver)
                if rx is None or tx.packet.kind not in {"FLOOD", "DATA"}:
                    return rx
                return replace(rx, snr_db=required_snr_db(self.radio.sf) + 10.0)

        for name, third_action in (
            ("meshecho-mag", "R"),
            ("meshecho-mag-periodic", "D"),
        ):
            with self.subTest(name=name):
                protocol = build_protocol(name)
                sim = HealthyMarginSimulator(
                    [Node(0, 0.0, 0.0), Node(1, 100.0, 0.0)],
                    RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
                    seed=17, max_hops=6, independent_random_streams=True,
                )
                for flow_id, when in enumerate((1.0, 20.0, 200.0), start=1):
                    sim.schedule(when, "app_send", (0, 1, flow_id))
                sim.run(200.0)
                self.assertEqual(
                    [event["action"] for event in protocol.action_events
                     if event["event"] == "decision"],
                    ["F", "R", third_action],
                )

    def test_older_route_ack_cannot_change_newly_committed_margin(self) -> None:
        class DelayedAckSimulator(Simulator):
            def transmit_later(self, sender, packet, delay_s, pending=None):
                if packet.kind == "ACK" and packet.flow_id == 2 and sender == 1:
                    delay_s += 15.0
                return super().transmit_later(sender, packet, delay_s, pending)

            def try_receive(self, tx, receiver):
                rx = super().try_receive(tx, receiver)
                if rx is None or tx.packet.kind not in {"FLOOD", "DATA"}:
                    return rx
                margin_db = 2.0 if tx.packet.flow_id == 2 else 10.0
                return replace(rx, snr_db=required_snr_db(self.radio.sf) + margin_db)

        protocol = build_protocol("meshecho-mag", Namespace(calm_route_ttl_s=15.0))
        sim = DelayedAckSimulator(
            [Node(0, 0.0, 0.0), Node(1, 100.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        for flow_id, when in enumerate((1.0, 10.0, 20.0), start=1):
            sim.schedule(when, "app_send", (0, 1, flow_id))

        metrics = sim.run(30.0)

        self.assertIsNotNone(metrics.flows[2].acked_at)
        self.assertEqual(protocol.destination_state[(0, 1)].last_commit_flow, 3)
        self.assertEqual(protocol.destination_state[(0, 1)].acked_margins_q, [20])

    def test_prefailure_discovery_caps_rreq_to_one_extra_hop(self) -> None:
        class CaptureRequestSimulator(Simulator):
            source_request_ttl = None

            def begin_transmission(self, sender, packet, pending):
                if packet.kind == "RREQ" and sender == packet.origin:
                    self.source_request_ttl = packet.ttl
                return super().begin_transmission(sender, packet, pending)

            def try_receive(self, tx, receiver):
                if tx.sender == 0 and receiver == 2:
                    return None
                rx = super().try_receive(tx, receiver)
                if rx is None or tx.packet.kind not in {"FLOOD", "DATA"}:
                    return rx
                margin_db = 10.0 if tx.packet.flow_id == 1 else 2.0
                return replace(rx, snr_db=required_snr_db(self.radio.sf) + margin_db)

        protocol = build_protocol("meshecho-mag")
        sim = CaptureRequestSimulator(
            [Node(0, 0.0, 0.0), Node(1, 100.0, 0.0), Node(2, 200.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        for flow_id, when in enumerate((1.0, 20.0, 40.0), start=1):
            sim.schedule(when, "app_send", (0, 2, flow_id))

        sim.run(40.0)

        self.assertEqual(sim.source_request_ttl, 3)


if __name__ == "__main__":
    unittest.main()
