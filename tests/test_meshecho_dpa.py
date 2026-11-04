import unittest
from dataclasses import replace
from unittest.mock import patch

from lora_mesh_sim import Node, RadioConfig, Simulator, build_protocol, parse_args


class MeshEchoDPATest(unittest.TestCase):
    def test_all_dpa_arms_are_available_from_cli(self) -> None:
        for name in ("meshecho-dpa", "meshecho-dpa-repeat", "meshecho-dpa-fr"):
            with self.subTest(name=name), patch("sys.argv", ["lora_mesh_sim.py", "--protocol", name]):
                self.assertEqual(parse_args().protocol, name)

    def run_two_branch(
        self, protocol_name, second_delay=0.8, drop_first_ack=False,
        second_path_override=None, hold_second_ack=False,
        first_path_override=None,
    ):
        class TwoBranchSimulator(Simulator):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.sent = []
                self.delayed_ack = None

            def begin_transmission(self, sender, packet, pending):
                if first_path_override is not None and sender == 1 and packet.kind == "FLOOD":
                    packet = replace(packet, path=first_path_override)
                if second_path_override is not None and sender == 2 and packet.kind == "FLOOD":
                    packet = replace(packet, path=second_path_override)
                previous = self.metrics.tx_count
                super().begin_transmission(sender, packet, pending)
                if self.metrics.tx_count > previous:
                    self.sent.append((sender, packet))

            def try_receive(self, tx, receiver):
                if (tx.sender, receiver) in {(0, 3), (1, 2), (2, 1)}:
                    return None
                if (drop_first_ack and receiver == 0 and tx.packet.kind == "ACK"
                        and tx.packet.path == (0, 1, 3)):
                    return None
                if (hold_second_ack and receiver == 0 and tx.packet.kind == "ACK"
                        and tx.packet.path == (0, 2, 3)):
                    self.delayed_ack = tx.packet
                    return None
                return super().try_receive(tx, receiver)

        protocol = build_protocol(protocol_name)
        protocol.flood_delay = lambda receiver=None, rx=None: (
            0.1 if receiver == 1 else second_delay
        )
        sim = TwoBranchSimulator(
            [Node(0, 0.0, 0.0), Node(1, 100.0, 100.0),
             Node(2, 100.0, -100.0), Node(3, 200.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 3, 1))
        if hold_second_ack:
            sim.schedule(
                31.0005, "protocol_timer",
                lambda: protocol.on_ack_packet(0, sim.delayed_ack),
            )

        metrics = sim.run(40.0 if hold_second_ack else 10.0)
        ack_paths = [packet.path for sender, packet in sim.sent
                     if sender == 3 and packet.kind == "ACK" and packet.flow_id == 1]
        return metrics, ack_paths, protocol

    def test_two_decoded_flood_paths_ack_on_distinct_realized_routes(self) -> None:
        metrics, ack_paths, protocol = self.run_two_branch("meshecho-dpa")
        self.assertEqual(ack_paths, [(0, 1, 3), (0, 2, 3)])
        opportunities = [event for event in protocol.action_events
                         if event["event"] == "dpa_second_path"]
        first_paths = [event for event in protocol.action_events
                       if event["event"] == "dpa_first_path"]
        ack_transmissions = [event for event in protocol.action_events
                             if event["event"] == "dpa_ack_tx"]
        source_acks = [event for event in protocol.action_events
                       if event["event"] == "dpa_source_ack_rx"]
        self.assertEqual(len(first_paths), 1)
        self.assertEqual(first_paths[0]["path"], (0, 1, 3))
        self.assertEqual([event["path"] for event in ack_transmissions], ack_paths)
        on_path_acks = [event for event in source_acks if event["on_path"]]
        self.assertEqual([event["path"] for event in on_path_acks], ack_paths)
        self.assertEqual([event["accepted"] for event in on_path_acks], [True, False])
        self.assertEqual(len(opportunities), 1)
        self.assertEqual(opportunities[0]["first_path"], (0, 1, 3))
        self.assertEqual(opportunities[0]["second_path"], (0, 2, 3))
        self.assertIsNotNone(metrics.flows[1].delivered_at)
        self.assertIsNotNone(metrics.flows[1].acked_at)

    def test_matched_extra_ack_repeats_first_path(self) -> None:
        metrics, ack_paths, _ = self.run_two_branch("meshecho-dpa-repeat")
        self.assertEqual(ack_paths, [(0, 1, 3), (0, 1, 3)])
        self.assertIsNotNone(metrics.flows[1].acked_at)

    def test_single_ack_control_uses_only_first_decoded_path(self) -> None:
        metrics, ack_paths, _ = self.run_two_branch("meshecho-dpa-fr")
        self.assertEqual(ack_paths, [(0, 1, 3)])
        self.assertIsNotNone(metrics.flows[1].acked_at)

    def test_late_second_path_does_not_ack_and_window_state_expires(self) -> None:
        _, ack_paths, protocol = self.run_two_branch("meshecho-dpa", second_delay=4.0)
        self.assertEqual(ack_paths, [(0, 1, 3)])
        self.assertEqual(protocol.first_flood_paths, {})
        self.assertEqual(protocol.second_ack_flows, set())

    def test_destination_keeps_at_most_eight_active_ack_windows(self) -> None:
        class NoSourceAckSimulator(Simulator):
            def try_receive(self, tx, receiver):
                if receiver == 0 and tx.packet.kind == "ACK":
                    return None
                return super().try_receive(tx, receiver)

        protocol = build_protocol("meshecho-dpa")
        sim = NoSourceAckSimulator(
            [Node(0, 0.0, 0.0), Node(1, 100.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        for flow_id in range(1, 10):
            sim.schedule(1.0 + 0.25 * (flow_id - 1), "app_send", (0, 1, flow_id))

        metrics = sim.run(3.5)

        self.assertEqual(sum(flow.delivered_at is not None for flow in metrics.flows.values()), 9)
        self.assertLessEqual(len(protocol.first_flood_paths), 8)

    def test_different_path_with_same_source_adjacent_hop_is_not_ack_diverse(self) -> None:
        class SharedFirstHopSimulator(Simulator):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.destination_paths = []
                self.ack_paths = []

            def begin_transmission(self, sender, packet, pending):
                previous = self.metrics.tx_count
                super().begin_transmission(sender, packet, pending)
                if self.metrics.tx_count > previous and sender == 3 and packet.kind == "ACK":
                    self.ack_paths.append(packet.path)

            def try_receive(self, tx, receiver):
                if tx.sender == 0 and receiver in {2, 3}:
                    return None
                rx = super().try_receive(tx, receiver)
                if rx is not None and receiver == 3 and tx.packet.kind == "FLOOD":
                    self.destination_paths.append(tx.packet.path + (receiver,))
                return rx

        protocol = build_protocol("meshecho-dpa")
        protocol.flood_delay = lambda receiver=None, rx=None: (
            0.1 if receiver == 1 else 0.8
        )
        sim = SharedFirstHopSimulator(
            [Node(0, 0.0, 0.0), Node(1, 100.0, 0.0),
             Node(2, 150.0, 100.0), Node(3, 200.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 3, 1))

        sim.run(10.0)

        self.assertIn((0, 1, 3), sim.destination_paths)
        self.assertIn((0, 1, 2, 3), sim.destination_paths)
        self.assertEqual(sim.ack_paths, [(0, 1, 3)])
        self.assertFalse(any(event["event"] == "dpa_second_path"
                             for event in protocol.action_events))

    def test_third_distinct_path_does_not_send_a_third_ack(self) -> None:
        class ThreeBranchSimulator(Simulator):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.destination_paths = []
                self.ack_paths = []

            def begin_transmission(self, sender, packet, pending):
                previous = self.metrics.tx_count
                super().begin_transmission(sender, packet, pending)
                if self.metrics.tx_count > previous and sender == 3 and packet.kind == "ACK":
                    self.ack_paths.append(packet.path)

            def try_receive(self, tx, receiver):
                if (tx.sender == 0 and receiver == 3
                        or tx.sender in {1, 2, 4} and receiver in {1, 2, 4}):
                    return None
                rx = super().try_receive(tx, receiver)
                if rx is not None and receiver == 3 and tx.packet.kind == "FLOOD":
                    self.destination_paths.append(tx.packet.path + (receiver,))
                return rx

        protocol = build_protocol("meshecho-dpa")
        protocol.flood_delay = lambda receiver=None, rx=None: {
            1: 0.1, 2: 0.8, 4: 1.5,
        }.get(receiver, 0.1)
        sim = ThreeBranchSimulator(
            [Node(0, 0.0, 0.0), Node(1, 100.0, 100.0),
             Node(2, 100.0, -100.0), Node(3, 200.0, 0.0),
             Node(4, 100.0, 200.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 3, 1))

        sim.run(10.0)

        self.assertEqual(len(sim.destination_paths), 3)
        self.assertEqual(sim.ack_paths, [(0, 1, 3), (0, 2, 3)])
        self.assertEqual(sum(event["event"] == "dpa_second_path"
                             for event in protocol.action_events), 1)

    def test_second_route_ack_rescues_first_route_ack_failure(self) -> None:
        diverse_metrics, diverse_acks, diverse = self.run_two_branch(
            "meshecho-dpa", drop_first_ack=True
        )
        repeat_metrics, _, _ = self.run_two_branch(
            "meshecho-dpa-repeat", drop_first_ack=True
        )
        single_metrics, _, _ = self.run_two_branch(
            "meshecho-dpa-fr", drop_first_ack=True
        )

        self.assertEqual(diverse_acks, [(0, 1, 3), (0, 2, 3)])
        self.assertIsNotNone(diverse_metrics.flows[1].acked_at)
        self.assertEqual(diverse.route_cache[0][3].path, (0, 2, 3))
        self.assertIsNone(repeat_metrics.flows[1].acked_at)
        self.assertIsNone(single_metrics.flows[1].acked_at)

    def test_path_claiming_a_different_source_cannot_trigger_extra_ack(self) -> None:
        _, ack_paths, protocol = self.run_two_branch(
            "meshecho-dpa", second_path_override=(9, 2)
        )
        self.assertEqual(ack_paths, [(0, 1, 3)])
        self.assertFalse(any(event["event"] == "dpa_second_path"
                             for event in protocol.action_events))

    def test_invalid_first_path_does_not_deliver_or_claim_first_ack(self) -> None:
        metrics, ack_paths, protocol = self.run_two_branch(
            "meshecho-dpa", first_path_override=(9, 1)
        )

        self.assertEqual(ack_paths, [(0, 2, 3)])
        self.assertEqual(metrics.flows[1].delivered_at is not None, True)
        self.assertEqual(protocol.route_cache[0][3].path, (0, 2, 3))
        first_paths = [event["path"] for event in protocol.action_events
                       if event["event"] == "dpa_first_path"]
        self.assertEqual(first_paths, [(0, 2, 3)])

    def test_first_path_must_end_at_actual_sender(self) -> None:
        _, ack_paths, protocol = self.run_two_branch(
            "meshecho-dpa", first_path_override=(0, 2)
        )

        self.assertEqual(ack_paths, [(0, 2, 3)])
        self.assertEqual(
            [event["path"] for event in protocol.action_events
             if event["event"] == "dpa_first_path"],
            [(0, 2, 3)],
        )

    def test_looped_second_path_cannot_trigger_extra_ack(self) -> None:
        _, ack_paths, protocol = self.run_two_branch(
            "meshecho-dpa", second_path_override=(0, 2, 0, 2)
        )
        self.assertEqual(ack_paths, [(0, 1, 3)])
        self.assertFalse(any(event["event"] == "dpa_second_path"
                             for event in protocol.action_events))

    def test_ack_claiming_wrong_destination_origin_cannot_confirm_route(self) -> None:
        class WrongOriginAckSimulator(Simulator):
            def begin_transmission(self, sender, packet, pending):
                if packet.kind == "ACK" and packet.flow_id == 1:
                    packet = replace(packet, origin=2)
                return super().begin_transmission(sender, packet, pending)

        protocol = build_protocol("meshecho-dpa")
        sim = WrongOriginAckSimulator(
            [Node(0, 0.0, 0.0), Node(1, 100.0, 0.0),
             Node(2, 300.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 1, 1))

        metrics = sim.run(10.0)

        self.assertIsNotNone(metrics.flows[1].delivered_at)
        self.assertIsNone(metrics.flows[1].acked_at)
        self.assertNotIn(1, protocol.route_cache[0])

    def test_ack_with_wrong_route_endpoint_cannot_confirm_route(self) -> None:
        class WrongPathAckSimulator(Simulator):
            def begin_transmission(self, sender, packet, pending):
                if packet.kind == "ACK" and packet.flow_id == 1:
                    packet = replace(packet, path=(0, 2), path_index=0)
                return super().begin_transmission(sender, packet, pending)

        protocol = build_protocol("meshecho-dpa")
        sim = WrongPathAckSimulator(
            [Node(0, 0.0, 0.0), Node(1, 100.0, 0.0),
             Node(2, 300.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 1, 1))

        metrics = sim.run(10.0)

        self.assertIsNotNone(metrics.flows[1].delivered_at)
        self.assertIsNone(metrics.flows[1].acked_at)
        self.assertNotIn(1, protocol.route_cache[0])

    def test_later_ack_cannot_overwrite_first_confirmed_route(self) -> None:
        metrics, ack_paths, protocol = self.run_two_branch("meshecho-dpa")

        self.assertEqual(len(ack_paths), 2)
        self.assertIsNotNone(metrics.flows[1].acked_at)
        commits = [event for event in protocol.action_events
                   if event["event"] == "commit" and event["flow_id"] == 1]
        self.assertEqual(len(commits), 1)
        self.assertEqual(commits[0]["path"], (0, 1, 3))
        self.assertEqual(protocol.route_cache[0][3].path, (0, 1, 3))

    def test_second_ack_after_application_deadline_cannot_confirm_route(self) -> None:
        metrics, ack_paths, protocol = self.run_two_branch(
            "meshecho-dpa", drop_first_ack=True, hold_second_ack=True
        )

        self.assertEqual(ack_paths, [(0, 1, 3), (0, 2, 3)])
        self.assertIsNotNone(metrics.flows[1].delivered_at)
        self.assertIsNone(metrics.flows[1].acked_at)
        self.assertNotIn(3, protocol.route_cache[0])


if __name__ == "__main__":
    unittest.main()
