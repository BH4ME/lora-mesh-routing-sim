import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from lora_mesh_sim import ICC_PROTOCOLS
from tools.run_icc_generalization_experiment import (
    GENERALIZATION_CASES,
    build_generalization_namespace,
    parse_args,
)
from tools.run_fair_multihop_probe import (
    ProbeRegimeError,
    run_one_probe,
    validate_non_degenerate_regime,
    write_report,
)


class IccGeneralizationExperimentTest(unittest.TestCase):
    def _feedback_args(self):
        case = next(
            case for case in GENERALIZATION_CASES if case.key == "feedback_fading"
        )
        return build_generalization_namespace(case, seeds=1, seed0=41)

    def _feedback_row(self, **changes):
        row = {
            "seed": 41,
            "protocol": "meshecho",
            "candidate_pair_count": 4,
            "selected_pair_mean_graph_hops": 2.25,
            "direct_prr_below_0_99": 0.20,
            "scheduled_unicast_flows": 40,
            "unicast_flows": 40,
            "scheduled_broadcast_flows": 0,
            "broadcast_flows": 0,
            "scheduled_distinct_unicast_pairs": 4,
            "observed_distinct_unicast_pairs": 4,
            "scheduled_min_flows_per_pair": 10,
            "scheduled_min_time_blocks_per_pair": 5,
            "scheduled_trace_sha256": "trace-a",
        }
        row.update(changes)
        return row

    def test_cases_include_unconditioned_random_and_deeper_multihop(self) -> None:
        keys = {case.key for case in GENERALIZATION_CASES}
        self.assertIn("random_pairs", keys)
        self.assertIn("deep_multihop", keys)
        self.assertIn("stale_fading", keys)

        random_args = build_generalization_namespace(
            next(case for case in GENERALIZATION_CASES if case.key == "random_pairs"),
            seeds=1,
            seed0=1,
        )
        self.assertEqual(random_args.pair_mode, "random")
        self.assertEqual(random_args.pair_count, 0)

        deep_args = build_generalization_namespace(
            next(case for case in GENERALIZATION_CASES if case.key == "deep_multihop"),
            seeds=1,
            seed0=1,
        )
        self.assertEqual(deep_args.pair_mode, "connected-multihop")
        self.assertGreaterEqual(deep_args.min_graph_hops, 3)
        self.assertGreaterEqual(deep_args.nodes, 100)

    def test_stale_fading_cases_have_paired_temporal_channel_and_ttl_control(self) -> None:
        long_case = next(
            case for case in GENERALIZATION_CASES if case.key == "stale_fading"
        )
        short_case = next(
            case
            for case in GENERALIZATION_CASES
            if case.key == "stale_fading_short_ttl"
        )
        long_args = build_generalization_namespace(long_case, seeds=1, seed0=1)
        short_args = build_generalization_namespace(short_case, seeds=1, seed0=1)
        self.assertGreater(long_args.temporal_fading_sigma_db, 0.0)
        self.assertGreater(long_args.temporal_fading_interval_s, 0.0)
        self.assertGreater(long_args.route_ttl_s, short_args.route_ttl_s)

    def test_feedback_cases_preserve_repeated_pair_regime_with_matched_rreq(self) -> None:
        expected = {
            "feedback_fading": (600.0, 6.0),
            "feedback_static": (600.0, 0.0),
            "feedback_fading_short_ttl": (30.0, 6.0),
        }
        for key, (ttl_s, fading_sigma_db) in expected.items():
            with self.subTest(case=key):
                case = next(case for case in GENERALIZATION_CASES if case.key == key)
                args = build_generalization_namespace(case, seeds=1, seed0=41)
                self.assertEqual(args.pair_mode, "connected-multihop")
                self.assertEqual(args.pair_count, 4)
                self.assertEqual(args.pair_schedule, "poisson")
                self.assertEqual(args.traffic, "unicast")
                self.assertTrue(args.matched_rreq_timing)
                self.assertTrue(args.require_repeated_pairs)
                self.assertEqual(args.route_ttl_s, ttl_s)
                self.assertEqual(args.temporal_fading_sigma_db, fading_sigma_db)
                self.assertEqual(args.temporal_fading_interval_s, 60.0)

        historical = next(
            case for case in GENERALIZATION_CASES if case.key == "stale_fading"
        )
        historical_args = build_generalization_namespace(historical, seeds=1, seed0=21)
        self.assertFalse(historical_args.matched_rreq_timing)
        self.assertFalse(historical_args.require_repeated_pairs)

    def test_cli_accepts_explicit_probe_comparators_without_changing_default(self) -> None:
        with patch("sys.argv", ["generalization", "--case", "feedback_fading"]):
            default_args = parse_args()
        with patch(
            "sys.argv",
            [
                "generalization",
                "--case",
                "feedback_fading",
                "--protocol",
                "prr-product",
            ],
        ):
            comparator_args = parse_args()

        self.assertIsNone(default_args.protocol)
        self.assertEqual(tuple(default_args.protocol or ICC_PROTOCOLS), ICC_PROTOCOLS)
        self.assertEqual(comparator_args.protocol, ["prr-product"])

    def test_cli_accepts_explicit_feedback_variants(self) -> None:
        with patch(
            "sys.argv",
            [
                "generalization",
                "--case",
                "feedback_fading",
                "--protocol",
                "meshecho-ack-evict",
                "--protocol",
                "prr-product-ack-evict",
            ],
        ):
            args = parse_args()

        self.assertEqual(
            args.protocol,
            ["meshecho-ack-evict", "prr-product-ack-evict"],
        )

    def test_feedback_probe_row_audits_every_reused_pair_and_time_block(self) -> None:
        case = next(
            case for case in GENERALIZATION_CASES if case.key == "feedback_fading"
        )
        args = build_generalization_namespace(case, seeds=1, seed0=41)
        row = run_one_probe(args, "meshecho", seed=41)
        pair_counts = json.loads(row["scheduled_pair_counts_json"])

        self.assertEqual(len(pair_counts), 4)
        self.assertEqual(row["scheduled_distinct_unicast_pairs"], 4)
        self.assertEqual(
            sum(item["flows"] for item in pair_counts), row["scheduled_unicast_flows"]
        )
        self.assertGreaterEqual(row["scheduled_min_flows_per_pair"], 2)
        self.assertGreaterEqual(row["scheduled_min_time_blocks_per_pair"], 2)
        self.assertTrue(all(item["time_blocks"] >= 2 for item in pair_counts))
        self.assertEqual(row["temporal_fading_sigma_db"], 6.0)
        self.assertEqual(row["temporal_fading_interval_s"], 60.0)

    def test_feedback_gate_rejects_protocol_specific_application_trace(self) -> None:
        args = self._feedback_args()
        row = self._feedback_row()
        other = dict(row, protocol="prr-product-mesh", scheduled_trace_sha256="trace-b")

        with self.assertRaisesRegex(ProbeRegimeError, "traffic trace differs"):
            validate_non_degenerate_regime([row, other], args)

    def test_feedback_gate_rejects_incomplete_observed_flow_count(self) -> None:
        row = self._feedback_row(unicast_flows=39)

        with self.assertRaisesRegex(ProbeRegimeError, "scheduled/observed unicast"):
            validate_non_degenerate_regime([row], self._feedback_args())

    def test_feedback_gate_rejects_missing_selected_pair(self) -> None:
        row = self._feedback_row(scheduled_distinct_unicast_pairs=3)

        with self.assertRaisesRegex(ProbeRegimeError, "selected source-destination pairs"):
            validate_non_degenerate_regime([row], self._feedback_args())

    def test_feedback_gate_rejects_pair_without_repeated_data(self) -> None:
        row = self._feedback_row(scheduled_min_flows_per_pair=1)

        with self.assertRaisesRegex(ProbeRegimeError, "at least two scheduled unicasts"):
            validate_non_degenerate_regime([row], self._feedback_args())

    def test_feedback_gate_rejects_pair_confined_to_one_time_block(self) -> None:
        row = self._feedback_row(scheduled_min_time_blocks_per_pair=1)

        with self.assertRaisesRegex(ProbeRegimeError, "at least two time blocks"):
            validate_non_degenerate_regime([row], self._feedback_args())

    def test_feedback_report_exposes_cache_and_false_invalidation_counts(self) -> None:
        args = self._feedback_args()
        row = run_one_probe(args, "meshecho-ack-evict", seed=41)
        validate_non_degenerate_regime([row], args)
        with TemporaryDirectory() as directory:
            report_path = Path(directory) / "meshecho_v2_1_24_icc2027_feedback_fading.md"
            write_report(report_path, [row], args)
            report = report_path.read_text(encoding="utf-8")

        self.assertIn("## Feedback Diagnostics", report)
        self.assertIn("ACK timeout invalidations", report)
        self.assertIn("after destination DATA", report)
        self.assertIn("Route-cache hits", report)
        self.assertIn("Route discoveries", report)
        self.assertIn("Total energy (J)", report)
        self.assertIn("## Repeated-Pair Audit", report)
        self.assertIn("Min scheduled unicasts/pair", report)
        self.assertIn("Min scheduled blocks/pair", report)
        self.assertIn("ACK-unconfirmed", report)
        self.assertNotIn("false positives", report)
        self.assertIn("--protocol meshecho-ack-evict", report)


if __name__ == "__main__":
    unittest.main()
