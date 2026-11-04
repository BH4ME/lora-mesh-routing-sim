"""Behavior checks for passive reverse-ACK hop tracing."""

import unittest

from lora_mesh_sim import Packet, Transmission
from tools.diagnose_flood_ack_hops import (
    analyze_ack_hops, run_diagnostic, run_exploration,
)
from tools.run_sr_experiment import SrCase


class FloodAckHopDiagnosticTests(unittest.TestCase):
    def test_distinguishes_missing_emission_failed_hop_and_late_source_decode(self) -> None:
        def ack(flow_id: int, path: tuple[int, ...], index: int) -> Packet:
            return Packet(
                kind="ACK", flow_id=flow_id, origin=path[-1], final_dst=path[0],
                ttl=6, created_at=0.0, protocol="meshecho-dhr-flood",
                request_id=flow_id, path=path, path_index=index, app_payload=False,
            )

        transmissions = [
            Transmission(9, 1, Packet(
                kind="FLOOD", flow_id=1, origin=0, final_dst=3, ttl=2,
                created_at=0.0, protocol="meshecho-dhr-flood", request_id=1,
                path=(0, 1),
            ), 4.8, 4.9),
            Transmission(10, 3, ack(1, (0, 1, 3), 1), 5.0, 5.1),
            Transmission(11, 1, ack(1, (0, 1, 3), 0), 5.1, 5.2),
            Transmission(20, 3, ack(2, (0, 3), 0), 31.9, 32.0),
        ]
        rows = [
            {"flow_id": 1, "src": 0, "dst": 3, "enqueued_at": 0.0,
             "deadline_at": 30.0, "delivered_at": 4.9, "acked_at": None,
             "delivery_by_deadline": True, "ack_by_deadline": False,
             "source_action": "F"},
            {"flow_id": 2, "src": 0, "dst": 3, "enqueued_at": 1.0,
             "deadline_at": 31.0, "delivered_at": 31.8, "acked_at": None,
             "delivery_by_deadline": False, "ack_by_deadline": False,
             "source_action": "R"},
            {"flow_id": 3, "src": 0, "dst": 3, "enqueued_at": 0.0,
             "deadline_at": 30.0, "delivered_at": None, "acked_at": None,
             "delivery_by_deadline": False, "ack_by_deadline": False,
             "source_action": "D-candidate"},
        ]

        observed = analyze_ack_hops(
            transmissions, {10: {1}, 11: set(), 20: {0}}, {10: 9, 11: 10},
            rows, first_deliveries={1: {"kind": "FLOOD", "received_at_s": 4.9}},
        )

        by_flow = {item["flow_id"]: item for item in observed["missing_flows"]}
        failed = by_flow[1]["ack_attempts"][0]
        self.assertEqual(failed["ack_path_hops"], 2)
        self.assertEqual(failed["trigger_packet_kind"], "FLOOD")
        self.assertEqual(failed["first_unphysical_reverse_hop"]["edge"], [1, 0])
        self.assertFalse(failed["source_physically_decoded"])
        self.assertEqual(by_flow[1]["first_delivery_kind"], "FLOOD")
        late = by_flow[2]["ack_attempts"][0]
        self.assertTrue(late["source_physically_decoded"])
        self.assertTrue(late["source_decode_after_deadline"])
        self.assertFalse(by_flow[2]["source_ack_accepted"])
        self.assertFalse(by_flow[3]["destination_emitted_ack"])

    def test_real_replay_reports_missing_flow_classification(self) -> None:
        case = SrCase(
            key="tiny_flood_ack_hops", nodes=4, area_m=100.0,
            duration_s=8.0, rate_per_min=30.0, pair_mode="random",
            pair_count=0, max_hops=3, temporal_fading_sigma_db=0.0,
        )

        result = run_diagnostic(14001, case=case)

        self.assertEqual(
            result["summary"]["missing_source_acks_by_deadline"],
            result["parity"]["baseline"]["scheduled_unicast_flows"]
            - result["parity"]["baseline"]["ack_by_deadline"],
        )
        self.assertEqual(len(result["missing_flows"]),
                         result["summary"]["missing_source_acks_by_deadline"])

    def test_unfinished_ack_at_drain_cutoff_is_censored_not_failed(self) -> None:
        packet = Packet(
            kind="ACK", flow_id=1, origin=3, final_dst=0, ttl=6,
            created_at=0.0, protocol="meshecho-dhr-flood", request_id=1,
            path=(0, 3), path_index=0, app_payload=False,
        )
        flow = {
            "flow_id": 1, "src": 0, "dst": 3, "enqueued_at": 0.0,
            "deadline_at": 30.0, "delivered_at": 29.9, "acked_at": None,
            "delivery_by_deadline": True, "ack_by_deadline": False,
            "source_action": "F",
        }

        observed = analyze_ack_hops(
            [Transmission(1, 3, packet, 29.99, 30.1)], {}, {}, [flow],
            observation_cutoff_s=30.0,
        )

        attempt = observed["missing_flows"][0]["ack_attempts"][0]
        self.assertEqual(attempt["termination"], "censored_at_observation_cutoff")
        self.assertIsNone(attempt["first_unphysical_reverse_hop"])

    def test_replay_preserves_original_trace_and_deadline_outcomes(self) -> None:
        case = SrCase(
            key="tiny_flood_ack_hops", nodes=4, area_m=100.0,
            duration_s=8.0, rate_per_min=30.0, pair_mode="random",
            pair_count=0, max_hops=3, temporal_fading_sigma_db=0.0,
        )

        result = run_diagnostic(14001, case=case)

        self.assertEqual(result["protocol"], "meshecho-dhr-flood")
        self.assertEqual(result["parity"]["baseline"], result["parity"]["replay"])
        self.assertGreater(result["parity"]["baseline"]["scheduled_unicast_flows"], 0)

    def test_exploration_keeps_observations_separate_from_counterfactuals(self) -> None:
        case = SrCase(
            key="tiny_flood_ack_hops", nodes=4, area_m=100.0,
            duration_s=8.0, rate_per_min=30.0, pair_mode="random",
            pair_count=0, max_hops=3, temporal_fading_sigma_db=0.0,
        )

        report = run_exploration(seeds=(14001,), case=case)

        self.assertIsNone(report["counterfactual_estimates"])
        self.assertEqual(
            report["summary"]["scheduled_unicast_flows"],
            report["runs"][0]["parity"]["baseline"]["scheduled_unicast_flows"],
        )
        self.assertEqual(
            report["summary"]["missing_source_acks_by_deadline"],
            report["runs"][0]["summary"]["missing_source_acks_by_deadline"],
        )
        self.assertIn("lora_mesh_sim.py", report["source_sha256"])


if __name__ == "__main__":
    unittest.main()
