import unittest
from dataclasses import replace
from unittest.mock import patch

from lora_mesh_sim import (
    FlowRecord, Node, Packet, RadioConfig, RxInfo, Simulator, build_protocol,
    parse_args,
)


class MeshEchoRACTest(unittest.TestCase):
    def test_all_rac_arms_are_available_from_cli(self) -> None:
        for name in ("meshecho-rac", "meshecho-rac-repeat", "meshecho-rac-fr"):
            with self.subTest(name=name), patch(
                "sys.argv", ["lora_mesh_sim.py", "--protocol", name],
            ):
                self.assertEqual(parse_args().protocol, name)

    def run_observation_packets(self, flow_ids, until_s):
        protocol = build_protocol("meshecho-rac")
        sim = Simulator(
            [Node(0, 0.0, 0.0), Node(1, 100.0, 0.0),
             Node(2, 150.0, 100.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        for offset, flow_id in enumerate(flow_ids):
            packet = Packet(
                kind="FLOOD", flow_id=flow_id, origin=0, final_dst=3,
                ttl=1, created_at=1.0 + offset,
                protocol="meshecho-rac", request_id=flow_id,
                path=(0, 1), path_index=1,
            )
            sim.transmit_later(1, packet, delay_s=1.0 + offset)
        sim.run(until_s)
        return protocol

    def run_diamond(
        self, protocol_name, drop_direct_ack=True, max_hops=6,
        hide_continuation_from_candidate=False, app_deadline_s=30.0,
        duplicate_destination_ack=False, second_candidate=False,
        matching_backoff_candidate=False,
        tamper_ack_path=False, hide_flood_from_candidate=False,
        drop_first_direct_ack_only=False, until_s=5.0,
    ):
        class AckGapSimulator(Simulator):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.sent = []
                self.duplicated_ack = False
                self.dropped_ack_once = False

            def begin_transmission(self, sender, packet, pending):
                if (tamper_ack_path and sender == 3 and packet.kind == "ACK"):
                    packet = replace(packet, path=(9, 1, 3))
                before = self.metrics.tx_count
                super().begin_transmission(sender, packet, pending)
                if self.metrics.tx_count > before:
                    self.sent.append((sender, packet))
                    if (duplicate_destination_ack and not self.duplicated_ack
                            and sender == 3 and packet.kind == "ACK"
                            and packet.repair_index == 255):
                        self.duplicated_ack = True
                        self.transmit_later(sender, packet, delay_s=1.0)

            def try_receive(self, tx, receiver):
                if tx.packet.kind == "FLOOD" and (tx.sender, receiver) in {
                    (0, 2), (0, 3), (0, 4), (0, 6),
                    (2, 3), (4, 3), (6, 3),
                }:
                    return None
                if (hide_flood_from_candidate and tx.packet.kind == "FLOOD"
                        and (tx.sender, receiver) == (1, 2)):
                    return None
                if (drop_direct_ack and tx.packet.kind == "ACK"
                        and (tx.sender, receiver) == (3, 1)):
                    return None
                if (drop_first_direct_ack_only and not self.dropped_ack_once
                        and tx.packet.kind == "ACK"
                        and (tx.sender, receiver) == (3, 1)):
                    self.dropped_ack_once = True
                    return None
                if (hide_continuation_from_candidate
                        and tx.packet.kind == "ACK"
                        and (tx.sender, receiver) == (1, 2)):
                    return None
                return super().try_receive(tx, receiver)

        protocol = build_protocol(protocol_name)
        protocol.app_deadline_s = app_deadline_s
        protocol.flood_delay = lambda receiver=None, rx=None: (
            10.0 if receiver in {2, 4, 6} else 0.1
        )
        nodes = [Node(0, 0.0, 0.0), Node(1, 100.0, 0.0),
                 Node(2, 150.0, 100.0), Node(3, 200.0, 0.0)]
        if second_candidate:
            nodes.append(Node(
                6 if matching_backoff_candidate else 4, 150.0, -100.0,
            ))
        sim = AckGapSimulator(
            nodes,
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=max_hops, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 3, 1))

        metrics = sim.run(until_s)
        return metrics, sim.sent, protocol

    def test_data_conditioned_offpath_ack_relay_recovers_first_flood(self) -> None:
        metrics, sent, protocol = self.run_diamond("meshecho-rac")

        self.assertIsNotNone(metrics.flows[1].delivered_at)
        self.assertIsNotNone(metrics.flows[1].acked_at)
        self.assertEqual(protocol.route_cache[0][3].path, (0, 1, 3))
        relays = [(sender, packet) for sender, packet in sent
                  if sender == 2 and packet.kind == "ACK"]
        self.assertEqual(len(relays), 1)
        self.assertEqual(relays[0][1].path, (0, 1, 3))
        self.assertEqual(relays[0][1].repair_index, 0)
        exposures = [event for event in protocol.action_events
                     if event["event"] == "rac_corridor_eligible"]
        self.assertEqual(len(exposures), 1)
        self.assertEqual(
            (exposures[0]["flow_id"], exposures[0]["src"],
             exposures[0]["dst"], exposures[0]["candidate"],
             exposures[0]["next_hop"], exposures[0]["path"]),
            (1, 0, 3, 2, 1, (0, 1, 3)),
        )
        self.assertEqual(
            sum(event["event"] == "rac_repair_tx"
                for event in protocol.action_events),
            1,
        )
        self.assertTrue(any(
            event["event"] == "rac_source_ack_rx"
            and event["accepted"] and event["repair_index"] == 0
            for event in protocol.action_events
        ))

    def test_ack_continuation_cancels_offpath_relay(self) -> None:
        metrics, sent, protocol = self.run_diamond(
            "meshecho-rac", drop_direct_ack=False
        )

        self.assertIsNotNone(metrics.flows[1].acked_at)
        self.assertFalse(any(sender == 2 and packet.kind == "ACK"
                             for sender, packet in sent))
        self.assertTrue(any(event["event"] == "rac_cancel"
                            for event in protocol.action_events))

    def test_same_wait_onpath_repeat_does_not_repair_broken_edge(self) -> None:
        repeat_metrics, repeat_sent, _ = self.run_diamond(
            "meshecho-rac-repeat"
        )
        single_metrics, single_sent, _ = self.run_diamond(
            "meshecho-rac-fr"
        )

        self.assertIsNone(repeat_metrics.flows[1].acked_at)
        self.assertIsNone(single_metrics.flows[1].acked_at)
        self.assertEqual(
            [packet.repair_index for sender, packet in repeat_sent
             if sender == 3 and packet.kind == "ACK"],
            [255, 1],
        )
        self.assertEqual(
            [packet.repair_index for sender, packet in single_sent
             if sender == 3 and packet.kind == "ACK"],
            [255],
        )
        self.assertFalse(any(sender == 2 and packet.kind == "ACK"
                             for sender, packet in repeat_sent))

    def test_offpath_repair_respects_remaining_ack_hop_budget(self) -> None:
        metrics, sent, _ = self.run_diamond("meshecho-rac", max_hops=2)

        self.assertIsNotNone(metrics.flows[1].delivered_at)
        self.assertIsNone(metrics.flows[1].acked_at)
        self.assertFalse(any(sender == 2 and packet.kind == "ACK"
                             for sender, packet in sent))

    def test_late_hidden_repair_does_not_duplicate_onpath_forward(self) -> None:
        metrics, sent, _ = self.run_diamond(
            "meshecho-rac", drop_direct_ack=False,
            hide_continuation_from_candidate=True,
        )

        self.assertIsNotNone(metrics.flows[1].acked_at)
        self.assertEqual(
            sum(sender == 2 and packet.kind == "ACK" for sender, packet in sent),
            1,
        )
        self.assertEqual(
            sum(sender == 1 and packet.kind == "ACK" for sender, packet in sent),
            1,
        )

    def test_repair_timer_does_not_transmit_after_application_deadline(self) -> None:
        metrics, sent, _ = self.run_diamond(
            "meshecho-rac", app_deadline_s=0.30,
        )

        self.assertIsNotNone(metrics.flows[1].delivered_at)
        self.assertIsNone(metrics.flows[1].acked_at)
        self.assertFalse(any(sender == 2 and packet.kind == "ACK"
                             for sender, packet in sent))

    def test_flood_observations_evict_oldest_flow_at_eight_per_node(self) -> None:
        protocol = self.run_observation_packets(range(1, 10), until_s=10.0)

        observed_at_two = [key[3] for key in protocol.flood_senders
                           if key[0] == 2]
        self.assertEqual(observed_at_two, list(range(2, 10)))

    def test_flood_observation_keeps_at_most_two_upstream_senders(self) -> None:
        protocol = build_protocol("meshecho-rac")
        sim = Simulator(
            [Node(node_id, 100.0 + node_id, 0.0)
             for node_id in (0, 1, 2, 4, 5)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        for offset, sender in enumerate((1, 4, 5)):
            packet = Packet(
                kind="FLOOD", flow_id=1, origin=0, final_dst=3,
                ttl=1, created_at=1.0, protocol="meshecho-rac",
                request_id=1, path=(0, sender), path_index=1,
            )
            sim.transmit_later(sender, packet, delay_s=1.0 + offset)
        sim.run(4.0)

        self.assertEqual(protocol.flood_senders[(2, 0, 3, 1, 1)], {1, 4})

    def test_flood_observation_expires_after_thirty_seconds(self) -> None:
        protocol = self.run_observation_packets([1], until_s=32.0)

        self.assertFalse(any(key[0] == 2 for key in protocol.flood_senders))

    def test_duplicate_destination_ack_triggers_only_one_offpath_repair(self) -> None:
        metrics, sent, protocol = self.run_diamond(
            "meshecho-rac", duplicate_destination_ack=True,
        )

        self.assertIsNotNone(metrics.flows[1].acked_at)
        self.assertEqual(
            sum(sender == 2 and packet.kind == "ACK" for sender, packet in sent),
            1,
        )
        self.assertEqual(
            sum(event["event"] == "rac_corridor_eligible"
                for event in protocol.action_events),
            1,
        )

    def test_candidates_use_distinct_local_backoffs(self) -> None:
        metrics, sent, _ = self.run_diamond(
            "meshecho-rac", second_candidate=True,
        )

        self.assertIsNotNone(metrics.flows[1].acked_at)
        self.assertEqual(
            sum(sender in {2, 4} and packet.kind == "ACK"
                for sender, packet in sent),
            1,
        )

    def test_candidate_rejects_ack_with_uncertified_source_path(self) -> None:
        metrics, sent, protocol = self.run_diamond(
            "meshecho-rac", tamper_ack_path=True,
        )

        self.assertIsNotNone(metrics.flows[1].delivered_at)
        self.assertIsNone(metrics.flows[1].acked_at)
        self.assertFalse(any(sender == 2 and packet.kind == "ACK"
                             for sender, packet in sent))
        self.assertFalse(any(event["event"] == "rac_corridor_eligible"
                             for event in protocol.action_events))

    def test_same_backoff_slot_candidates_can_still_collide(self) -> None:
        metrics, sent, _ = self.run_diamond(
            "meshecho-rac", second_candidate=True,
            matching_backoff_candidate=True,
        )

        self.assertIsNotNone(metrics.flows[1].delivered_at)
        self.assertIsNone(metrics.flows[1].acked_at)
        self.assertEqual(
            sum(sender in {2, 6} and packet.kind == "ACK"
                for sender, packet in sent),
            2,
        )

    def test_candidate_without_data_observation_cannot_repair(self) -> None:
        metrics, sent, protocol = self.run_diamond(
            "meshecho-rac", hide_flood_from_candidate=True,
        )

        self.assertIsNotNone(metrics.flows[1].delivered_at)
        self.assertIsNone(metrics.flows[1].acked_at)
        self.assertFalse(any(sender == 2 and packet.kind == "ACK"
                             for sender, packet in sent))
        self.assertFalse(any(event["event"] == "rac_corridor_eligible"
                             for event in protocol.action_events))

    def test_onpath_repeat_recovers_one_lost_ack_copy(self) -> None:
        repeated, sent, protocol = self.run_diamond(
            "meshecho-rac-repeat", drop_direct_ack=False,
            drop_first_direct_ack_only=True,
        )
        single, _, _ = self.run_diamond(
            "meshecho-rac-fr", drop_direct_ack=False,
            drop_first_direct_ack_only=True,
        )

        self.assertIsNotNone(repeated.flows[1].acked_at)
        self.assertIsNone(single.flows[1].acked_at)
        self.assertEqual(
            [packet.repair_index for sender, packet in sent
             if sender == 3 and packet.kind == "ACK"],
            [255, 1],
        )
        self.assertTrue(any(event["event"] == "rac_repeat_tx"
                            and event["sender"] == 3
                            for event in protocol.action_events))

    def test_repair_bytes_airtime_and_energy_are_charged(self) -> None:
        metrics, sent, _ = self.run_diamond("meshecho-rac")
        radio = RadioConfig(sf=7, shadow_sigma_db=0.0)
        ack_packets = [packet for _, packet in sent if packet.kind == "ACK"]

        self.assertEqual(metrics.ack_tx, len(ack_packets))
        self.assertEqual(
            [packet.wire_size_bytes(24)
             - replace(packet, repair_index=None).wire_size_bytes(24)
             for packet in ack_packets],
            [1] * len(ack_packets),
        )
        self.assertAlmostEqual(
            metrics.total_airtime_s,
            sum(radio.packet_toa_s(packet) for _, packet in sent),
        )
        self.assertAlmostEqual(
            metrics.tx_energy_j,
            radio.supply_voltage_v * radio.tx_current_ma / 1000.0
            * metrics.total_airtime_s,
        )

    def test_seen_ack_hop_state_expires_after_flow_deadline(self) -> None:
        _, _, protocol = self.run_diamond("meshecho-rac", until_s=32.0)

        self.assertFalse(protocol.seen_ack_hops)

    def test_repair_attempt_history_expires_at_flow_deadline(self) -> None:
        _, _, protocol = self.run_diamond("meshecho-rac", until_s=31.1)

        self.assertFalse(protocol.attempted_repairs)

    def test_pending_repairs_evict_oldest_at_eight_per_node(self) -> None:
        protocol = build_protocol("meshecho-rac")
        sim = Simulator(
            [Node(node_id, 100.0 * node_id, 0.0)
             for node_id in range(4)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.now = 1.0
        rx = RxInfo(sender=3, rx_power_dbm=-50.0, snr_db=10.0,
                    sinr_db=10.0, collided=False)
        for flow_id in range(1, 10):
            sim.metrics.flows[flow_id] = FlowRecord(flow_id, 0, 3, 1.0)
            protocol.flow_data_actions[flow_id] = "F"
            protocol.flood_senders[(2, 0, 3, flow_id, flow_id)] = {1}
            ack = Packet(
                kind="ACK", flow_id=flow_id, origin=3, final_dst=0,
                ttl=6, created_at=1.0, protocol="meshecho-rac",
                request_id=flow_id, path=(0, 1, 3), path_index=1,
                app_payload=False, repair_index=255,
            )
            protocol.on_receive(2, ack, rx)

        pending_flows = [key[1] for key in protocol.scheduled_repairs
                         if key[0] == 2]
        self.assertEqual(sorted(pending_flows), list(range(2, 10)))

    def test_pending_repeats_evict_oldest_at_eight_per_node(self) -> None:
        protocol = build_protocol("meshecho-rac-repeat")
        Simulator(
            [Node(node_id, 100.0 * node_id, 0.0)
             for node_id in range(4)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        for flow_id in range(1, 10):
            protocol.flow_data_actions[flow_id] = "F"
            ack = Packet(
                kind="ACK", flow_id=flow_id, origin=3, final_dst=0,
                ttl=6, created_at=1.0, protocol="meshecho-rac-repeat",
                request_id=flow_id, path=(0, 1, 3), path_index=1,
                app_payload=False, repair_index=255,
            )
            protocol.on_transmit(3, ack, 1.0, 1.05)

        pending_flows = [key[1] for key in protocol.scheduled_repeats
                         if key[0] == 3]
        self.assertEqual(sorted(pending_flows), list(range(2, 10)))

    def test_duplicate_initial_ack_schedules_only_one_local_repeat(self) -> None:
        _, sent, _ = self.run_diamond(
            "meshecho-rac-repeat", duplicate_destination_ack=True,
        )

        self.assertEqual(
            [packet.repair_index for sender, packet in sent
             if sender == 3 and packet.kind == "ACK"],
            [255, 1, 255],
        )


if __name__ == "__main__":
    unittest.main()
