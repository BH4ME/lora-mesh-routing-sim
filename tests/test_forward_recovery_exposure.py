"""Public-behavior checks for passive fixed-F forward-recovery exposure."""

from __future__ import annotations

import unittest
import hashlib
import json
import tempfile
from pathlib import Path

from lora_mesh_sim import Packet, Transmission
from tools.diagnose_forward_recovery_exposure import (
    analyze_forward_recovery, build_report, run_diagnostic, write_report,
)
from tools.run_sr_experiment import SrCase


class ForwardRecoveryExposureTests(unittest.TestCase):
    def test_attributes_initial_route_and_recovery_flood_without_double_counting(self) -> None:
        def packet(kind: str, path: tuple[int, ...], marker: int | None) -> Packet:
            return Packet(
                kind=kind, flow_id=7, origin=0, final_dst=3, ttl=6,
                created_at=0.0, protocol="meshecho-dhr-flood", request_id=7,
                path=path, repair_index=marker,
            )

        flow_rows = [{
            "flow_id": 7, "src": 0, "dst": 3, "source_action": "R",
            "enqueued_at": 0.0, "deadline_at": 30.0,
            "delivered_at": 16.0, "acked_at": None,
            "delivery_by_deadline": True, "ack_by_deadline": False,
        }]
        events = [
            {"event": "dhr_guard", "time": 15.0, "flow_id": 7,
             "admitted": True, "selected_action": "F", "reason": "admitted"},
            {"event": "dhr_recovery_tx", "time": 15.2, "flow_id": 7,
             "action": "F", "repair_index": 2},
            {"event": "dhr_destination_rx", "time": 16.0,
             "flow_id": 7, "repair_index": 2, "duplicate": False},
            {"event": "dhr_destination_rx", "time": 16.4,
             "flow_id": 7, "repair_index": 2, "duplicate": True},
        ]
        transmissions = [
            Transmission(1, 0, packet("DATA", (0, 1, 3), None), 0.1, 0.2),
            Transmission(2, 0, packet("FLOOD", (0,), 2), 15.2, 15.4),
            Transmission(3, 1, packet("FLOOD", (0, 1), 2), 15.5, 15.8),
            Transmission(4, 2, packet("FLOOD", (0, 2), 2), 16.1, 16.5),
        ]
        flood_decodes = [
            {"flow_id": 7, "time": 16.0, "path": (0, 1, 3), "tx_id": 3},
            {"flow_id": 7, "time": 16.4, "path": (0, 2, 3), "tx_id": 4},
        ]

        observed = analyze_forward_recovery(
            flow_rows, events, transmissions, flood_decodes, cutoff_s=30.0,
        )

        self.assertEqual(observed["summary"]["admitted_r_timeouts"], 1)
        self.assertEqual(observed["summary"]["initial_r_delivered_before_guard"], 0)
        self.assertEqual(observed["summary"]["f_recovery_first_delivery"], 1)
        self.assertEqual(observed["summary"]["f_recovery_any_destination_decode"], 1)
        flow = observed["flows"][0]
        self.assertEqual(flow["source_known_initial_path_hops"], 2)
        self.assertEqual(flow["deadline_remaining_at_guard_s"], 15.0)
        self.assertEqual(flow["f_recovery_decoded_path_hops"], [2, 2])
        self.assertEqual(flow["f_recovery_timely_decoded_path_hops"], [2, 2])
        self.assertEqual(flow["f_recovery_first_delivery_path_hops"], 2)
        self.assertEqual(
            observed["summary"]["first_f_path_minus_initial_hops"],
            {"negative": 0, "zero": 1, "plus_1": 0, "plus_2_or_more": 0},
        )
        self.assertEqual(observed["flood_tx_by_depth"]["0"]["tx"], 1)
        self.assertAlmostEqual(observed["flood_tx_by_depth"]["0"]["airtime_s"], 0.2)
        self.assertEqual(observed["flood_tx_by_depth"]["1"]["tx"], 2)
        self.assertAlmostEqual(observed["flood_tx_by_depth"]["1"]["airtime_s"], 0.7)

    def test_tracks_forwarding_that_starts_after_first_f_destination_decode(self) -> None:
        packet = Packet(
            kind="FLOOD", flow_id=4, origin=0, final_dst=3, ttl=6,
            created_at=0.0, protocol="meshecho-dhr-flood", request_id=4,
            path=(0, 2), repair_index=2,
        )
        observed = analyze_forward_recovery(
            [{"flow_id": 4, "src": 0, "dst": 3, "source_action": "R",
              "enqueued_at": 0.0, "deadline_at": 30.0,
              "delivered_at": 16.0, "acked_at": None,
              "delivery_by_deadline": True, "ack_by_deadline": False}],
            [{"event": "dhr_guard", "time": 15.0, "flow_id": 4,
              "admitted": True, "selected_action": "F", "reason": "admitted"},
             {"event": "dhr_destination_rx", "time": 16.0, "flow_id": 4,
              "repair_index": 2, "duplicate": False}],
            [Transmission(9, 2, packet, 16.1, 16.5)],
            [{"flow_id": 4, "time": 16.0, "path": (0, 1, 3), "tx_id": 8}],
            cutoff_s=30.0,
        )

        self.assertEqual(observed["summary"]["f_recovery_tx_after_first_f_decode"], 1)
        self.assertAlmostEqual(
            observed["summary"]["f_recovery_airtime_after_first_f_decode_s"], 0.4,
        )
        self.assertEqual(observed["flood_tx_by_depth"]["1"]["tx_after_first_f_decode"], 1)

    def test_counts_relay_airtime_after_initial_r_destination_delivery(self) -> None:
        source = Packet(
            kind="FLOOD", flow_id=5, origin=0, final_dst=3, ttl=6,
            created_at=0.0, protocol="meshecho-dhr-flood", request_id=5,
            path=(0,), repair_index=2,
        )
        relay = Packet(
            kind="FLOOD", flow_id=5, origin=0, final_dst=3, ttl=5,
            created_at=0.0, protocol="meshecho-dhr-flood", request_id=5,
            path=(0, 2), repair_index=2,
        )
        observed = analyze_forward_recovery(
            [{"flow_id": 5, "src": 0, "dst": 3, "source_action": "R",
              "enqueued_at": 0.0, "deadline_at": 30.0,
              "delivered_at": 14.8, "acked_at": None,
              "delivery_by_deadline": True, "ack_by_deadline": False}],
            [{"event": "dhr_guard", "time": 15.0, "flow_id": 5,
              "admitted": True, "selected_action": "F", "reason": "admitted"},
             {"event": "dhr_destination_rx", "time": 14.8, "flow_id": 5,
              "repair_index": None, "duplicate": False},
             {"event": "dhr_destination_rx", "time": 16.0, "flow_id": 5,
              "repair_index": 2, "duplicate": True}],
            [Transmission(6, 0, source, 15.0, 15.1),
             Transmission(7, 2, relay, 15.2, 15.6)],
            [{"flow_id": 5, "time": 16.0, "path": (0, 2, 3), "tx_id": 7}],
            cutoff_s=30.0,
        )

        self.assertEqual(observed["summary"]["initial_r_delivered_before_guard"], 1)
        self.assertEqual(observed["summary"]["f_recovery_first_delivery"], 0)
        self.assertEqual(
            observed["summary"]["f_recovery_relay_tx_after_first_destination_delivery"],
            1,
        )
        self.assertAlmostEqual(
            observed["summary"]["f_recovery_relay_airtime_after_first_destination_delivery_s"],
            0.4,
        )

    def test_rejects_physical_decode_log_that_disagrees_with_protocol_receipts(self) -> None:
        flow = {"flow_id": 6, "src": 0, "dst": 3, "source_action": "R",
                "enqueued_at": 0.0, "deadline_at": 30.0,
                "delivered_at": 16.0, "acked_at": None,
                "delivery_by_deadline": True, "ack_by_deadline": False}

        with self.assertRaisesRegex(AssertionError, "F decode attribution"):
            analyze_forward_recovery(
                [flow],
                [{"event": "dhr_destination_rx", "time": 16.0,
                  "flow_id": 6, "repair_index": 2, "duplicate": False}],
                [], [], cutoff_s=30.0,
            )

    def test_real_replay_preserves_all_flow_actions_and_full_tx_trace(self) -> None:
        case = SrCase(
            key="tiny_forward_recovery", nodes=4, area_m=100.0,
            duration_s=8.0, rate_per_min=30.0, pair_mode="random",
            pair_count=0, max_hops=3, temporal_fading_sigma_db=0.0,
        )

        result = run_diagnostic(13001, case=case)

        self.assertEqual(result["protocol"], "meshecho-dhr-flood")
        self.assertTrue(result["parity"]["per_flow_exact_timestamps"])
        self.assertTrue(result["parity"]["action_events_exact"])
        self.assertTrue(result["parity"]["full_tx_trace_exact"])
        self.assertEqual(
            result["parity"]["baseline_scheduled_trace_sha256"],
            result["parity"]["plain_scheduled_trace_sha256"],
        )
        self.assertEqual(
            result["parity"]["plain_full_tx_trace_sha256"],
            result["parity"]["observed_full_tx_trace_sha256"],
        )
        self.assertGreater(result["analysis"]["summary"]["scheduled_unicast_flows"], 0)

    def test_report_aggregates_only_new_exploratory_runs_and_hashes_its_artifact(self) -> None:
        case = SrCase(
            key="tiny_forward_recovery_report", nodes=4, area_m=100.0,
            duration_s=8.0, rate_per_min=30.0, pair_mode="random",
            pair_count=0, max_hops=3, temporal_fading_sigma_db=0.0,
        )

        report = build_report((13001,), case=case)

        self.assertEqual(report["seed_use"], "mechanical-test-only")
        self.assertIsNone(report["counterfactual_estimates"])
        self.assertEqual(report["summary"]["scheduled_unicast_flows"],
                         report["runs"][0]["analysis"]["summary"]["scheduled_unicast_flows"])
        self.assertIn("lora_mesh_sim.py", report["source_sha256"])
        self.assertIn("tests/test_forward_recovery_exposure.py", report["source_sha256"])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            digest = write_report(report, path)
            self.assertEqual(digest, hashlib.sha256(path.read_bytes()).hexdigest())
            self.assertEqual(json.loads(path.read_text())["seeds"], [13001])

    def test_reserved_bar_holdout_and_unregistered_default_seeds_are_refused(self) -> None:
        with self.assertRaisesRegex(ValueError, "BAR holdout"):
            run_diagnostic(17001)
        with self.assertRaisesRegex(ValueError, "only exploratory seeds"):
            run_diagnostic(18004)


if __name__ == "__main__":
    unittest.main()
