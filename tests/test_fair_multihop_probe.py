import json
import unittest
from argparse import Namespace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from tools.run_icc_sensitivity_experiments import (
    DEFAULT_SENSITIVITY_CASES,
    build_probe_namespace,
)
from tools.run_icc_generalization_experiment import (
    GENERALIZATION_CASES,
    build_generalization_namespace,
)
from tools.run_fair_multihop_probe import (
    ProbeRegimeError,
    parse_args,
    validate_non_degenerate_regime,
    run_one_probe,
    write_report,
)


class FairMultihopProbeTest(unittest.TestCase):
    def test_cli_accepts_fixed_once_pair_schedule(self) -> None:
        with patch("sys.argv", ["probe", "--pair-schedule", "fixed-once"]):
            args = parse_args()

        self.assertEqual(args.pair_schedule, "fixed-once")

    def test_cli_accepts_matched_rreq_timing(self) -> None:
        with patch("sys.argv", ["probe", "--matched-rreq-timing"]):
            args = parse_args()

        self.assertTrue(args.matched_rreq_timing)

    def test_cli_accepts_optional_budgeted_policy(self) -> None:
        with patch("sys.argv", ["probe", "--protocol", "meshecho-budgeted"]):
            args = parse_args()

        self.assertEqual(args.protocol, ["meshecho-budgeted"])

    def test_prr_product_is_available_as_an_explicit_fair_comparator(self) -> None:
        with patch("sys.argv", ["probe", "--protocol", "prr-product"]):
            args = parse_args()

        self.assertEqual(args.protocol, ["prr-product"])

    def _fixed_once_args(self) -> Namespace:
        case = next(case for case in DEFAULT_SENSITIVITY_CASES if case.key == "load4")
        args = build_probe_namespace(case, seeds=1, seed0=1)
        args.rate_per_min = 1.0
        args.traffic = "unicast"
        args.pair_schedule = "fixed-once"
        return args

    def _quality_args(self) -> Namespace:
        return Namespace(
            pair_mode="connected-multihop",
            pair_count=4,
            min_graph_hops=2,
            min_direct_prr_below_0_99=0.10,
            min_selected_pair_mean_graph_hops=2.0,
        )

    def _row(self, **overrides: object) -> dict[str, object]:
        row: dict[str, object] = {
            "seed": 1,
            "protocol": "smart-calm",
            "candidate_pair_count": 4,
            "selected_pair_mean_graph_hops": 2.25,
            "direct_prr_below_0_99": 0.40,
        }
        row.update(overrides)
        return row

    def test_non_degenerate_regime_accepts_qualified_seed(self) -> None:
        validate_non_degenerate_regime([self._row()], self._quality_args())

    def test_non_degenerate_regime_rejects_saturated_links(self) -> None:
        with self.assertRaisesRegex(ProbeRegimeError, "direct-link PRR"):
            validate_non_degenerate_regime(
                [self._row(direct_prr_below_0_99=0.01)], self._quality_args()
            )

    def test_non_degenerate_regime_rejects_short_or_incomplete_pair_pool(self) -> None:
        args = self._quality_args()
        with self.assertRaisesRegex(ProbeRegimeError, "pair pool"):
            validate_non_degenerate_regime(
                [self._row(candidate_pair_count=3)], args
            )
        with self.assertRaisesRegex(ProbeRegimeError, "graph hops"):
            validate_non_degenerate_regime(
                [self._row(selected_pair_mean_graph_hops=1.5)], args
            )

    def test_fixed_once_gate_rejects_incomplete_observed_workload(self) -> None:
        args = self._quality_args()
        args.pair_schedule = "fixed-once"
        row = self._row(
            scheduled_unicast_flows=4,
            scheduled_distinct_unicast_pairs=4,
            scheduled_broadcast_flows=0,
            unicast_flows=3,
            observed_distinct_unicast_pairs=3,
            broadcast_flows=0,
        )

        with self.assertRaisesRegex(ProbeRegimeError, "fixed-once workload"):
            validate_non_degenerate_regime([row], args)

    def test_fixed_once_gate_rejects_protocol_specific_traffic_trace(self) -> None:
        args = self._quality_args()
        args.pair_schedule = "fixed-once"
        counts = {
            "scheduled_unicast_flows": 4,
            "scheduled_distinct_unicast_pairs": 4,
            "scheduled_broadcast_flows": 0,
            "unicast_flows": 4,
            "observed_distinct_unicast_pairs": 4,
            "broadcast_flows": 0,
        }
        first = self._row(protocol="meshecho", scheduled_trace_sha256="trace-a", **counts)
        second = self._row(protocol="etx-mesh", scheduled_trace_sha256="trace-b", **counts)

        with self.assertRaisesRegex(ProbeRegimeError, "traffic trace"):
            validate_non_degenerate_regime([first, second], args)

    def test_probe_reports_route_discovery_health(self) -> None:
        args = Namespace(
            scenario="test",
            nodes=8,
            area_m=12000.0,
            duration_s=10.0,
            rate_per_min=1.0,
            traffic="unicast",
            pair_mode="random",
            pair_count=0,
            edge_prr_threshold=0.9,
            min_graph_hops=2,
            max_graph_hops=4,
            sf=7,
            bw_hz=125_000,
            cr=1,
            payload_bytes=32,
            tx_power_dbm=17.0,
            path_loss_exp=2.75,
            shadow_sigma_db=4.0,
            capture_threshold_db=6.0,
            max_hops=7,
            smart_max_timeout_retries=0,
            repeater_ratio=0.0,
            independent_rng_streams=True,
            seeds=1,
            seed0=1,
        )

        row = run_one_probe(args, "meshcore", seed=1)

        self.assertIn("route_discovery_success_rate", row)
        self.assertIn("rrep_rreq_tx_ratio", row)
        self.assertGreaterEqual(float(row["route_discovery_success_rate"]), 0.0)
        self.assertLessEqual(float(row["route_discovery_success_rate"]), 1.0)
        self.assertGreaterEqual(float(row["rrep_rreq_tx_ratio"]), 0.0)
        self.assertEqual(row["smart_max_timeout_retries"], 0)

    def test_fixed_once_sends_every_selected_pair_as_unicast(self) -> None:
        row = run_one_probe(self._fixed_once_args(), "meshecho", seed=1)

        self.assertEqual(row["unicast_flows"], 24)
        self.assertEqual(row["broadcast_flows"], 0)

    def test_fixed_once_reports_scheduled_and_observed_pair_denominators(self) -> None:
        row = run_one_probe(self._fixed_once_args(), "meshecho", seed=1)

        self.assertEqual(row["pair_schedule"], "fixed-once")
        self.assertEqual(row["scheduled_unicast_flows"], 24)
        self.assertEqual(row["scheduled_distinct_unicast_pairs"], 24)
        self.assertEqual(row["observed_distinct_unicast_pairs"], 24)
        self.assertEqual(row["scheduled_broadcast_flows"], 0)
        self.assertAlmostEqual(row["scheduled_rate_per_min"], 2.4)

    def test_fixed_once_uses_the_same_trace_for_paired_protocols(self) -> None:
        args = self._fixed_once_args()
        echo = run_one_probe(args, "meshecho", seed=1)
        etx = run_one_probe(args, "etx", seed=1)

        self.assertEqual(
            echo["scheduled_trace_sha256"], etx["scheduled_trace_sha256"]
        )

    def test_fixed_once_report_discloses_actual_workload_denominators(self) -> None:
        args = self._fixed_once_args()
        row = run_one_probe(args, "meshecho", seed=1)
        with TemporaryDirectory() as directory:
            report = Path(directory) / "report.md"
            write_report(report, [row], args)
            content = report.read_text(encoding="utf-8")

        self.assertIn("2.4 scheduled flows/min", content)
        self.assertIn("## Application Denominators", content)
        self.assertIn("| meshecho | 24 | 24 | 24-24 | 24-24 |", content)

    def test_matched_timing_reports_each_discovery_candidate_set(self) -> None:
        args = self._fixed_once_args()
        args.matched_rreq_timing = True
        row = run_one_probe(args, "meshecho", seed=1)

        self.assertEqual(row["matched_rreq_timing"], 1)
        self.assertEqual(row["discovery_record_count"], 24)
        fingerprints = json.loads(row["discovery_candidate_fingerprints_json"])
        self.assertEqual(len(fingerprints), 24)
        self.assertEqual(
            row["discovery_candidate_path_total"],
            sum(record["candidate_count"] for record in fingerprints),
        )
        self.assertEqual(
            row["discovery_multi_candidate_count"],
            sum(record["candidate_count"] >= 2 for record in fingerprints),
        )
        self.assertTrue(all(len(record["sha256"]) == 64 for record in fingerprints))
        records = json.loads(row["discovery_records_json"])
        self.assertEqual(len(records), 24)
        self.assertEqual(len({tuple(record["key"]) for record in records}), 24)
        self.assertEqual(
            row["discovery_candidate_path_total"],
            sum(len(record["candidate_paths"]) for record in records),
        )
        self.assertTrue(
            all(
                record["selected_path"] is None
                or record["selected_path"] in record["candidate_paths"]
                for record in records
            )
        )

    def test_report_summarizes_discovery_candidate_audit(self) -> None:
        args = self._fixed_once_args()
        args.matched_rreq_timing = True
        row = run_one_probe(args, "meshecho", seed=1)
        with TemporaryDirectory() as directory:
            report = Path(directory) / "report.md"
            write_report(report, [row], args)
            content = report.read_text(encoding="utf-8")

        self.assertIn("## Discovery Candidate Audit", content)
        self.assertIn("discovery_candidate_fingerprints_json", content)
        self.assertIn(
            f"| meshecho | {row['discovery_record_count']} | "
            f"{row['discovery_candidate_path_total']} | "
            f"{row['discovery_multi_candidate_count']} |",
            content,
        )

    def test_report_names_only_baselines_in_the_run(self) -> None:
        args = self._fixed_once_args()
        rows = [
            run_one_probe(args, protocol, seed=1)
            for protocol in ("meshecho", "etx")
        ]
        with TemporaryDirectory() as directory:
            report = Path(directory) / "report.md"
            write_report(report, rows, args)
            content = report.read_text(encoding="utf-8")

        self.assertIn("compared with ETX", content)
        self.assertNotIn("compared with managed flooding", content)
        self.assertNotIn("ETX/ETT quality-metric baselines", content)
        self.assertNotIn("shared traffic and discovery budget", content)

    def test_prr_product_probe_reports_model_assumptions_and_pairing(self) -> None:
        args = self._fixed_once_args()
        args.matched_rreq_timing = True
        echo = run_one_probe(args, "meshecho", seed=1)
        product = run_one_probe(args, "prr-product", seed=1)

        self.assertEqual(product["protocol"], "prr-product-mesh")
        self.assertEqual(product["matched_rreq_timing"], 1)
        self.assertEqual(product["fallback_forward_count"], 0)
        self.assertEqual(
            echo["scheduled_trace_sha256"], product["scheduled_trace_sha256"]
        )
        with TemporaryDirectory() as directory:
            report_path = Path(directory) / "probe.md"
            write_report(report_path, [echo, product], args)
            content = report_path.read_text(encoding="utf-8")

        self.assertIn("MeshEcho vs prr-product-mesh", content)
        self.assertIn("--protocol prr-product", content)
        self.assertIn("model-derived PRR", content)
        self.assertIn("no retry or fallback", content)

    def test_poisson_connected_report_discloses_pair_reuse_and_link_fraction(self) -> None:
        args = self._fixed_once_args()
        args.pair_schedule = "poisson"
        args.report_cache_reuse = False
        row = run_one_probe(args, "meshecho", seed=1)
        with TemporaryDirectory() as directory:
            report = Path(directory) / "report.md"
            write_report(report, [row], args)
            content = report.read_text(encoding="utf-8")

        self.assertIn("cycles through a selected connected-pair pool", content)
        self.assertIn(
            f"below 0.50 PRR: {float(row['direct_prr_below_0_50']):.3f}",
            content,
        )
        self.assertNotIn("It removes fixed-pair reuse", content)
        self.assertNotIn("substantial fraction", content)
        self.assertIn("each seed has equal weight", content)
        self.assertIn("pooled flow counts", content)

    def test_generalization_report_reproduces_case_seed_and_prefix(self) -> None:
        case = next(case for case in GENERALIZATION_CASES if case.key == "random_pairs")
        args = build_generalization_namespace(case, seeds=1, seed0=21)
        row = run_one_probe(args, "meshecho", seed=21)
        with TemporaryDirectory() as directory:
            report = Path(directory) / (
                "meshecho_v2_1_23_icc2027_generalization_random_pairs.md"
            )
            write_report(report, [row], args)
            content = report.read_text(encoding="utf-8")

        self.assertIn("--case random_pairs", content)
        self.assertIn("--seeds 1 --seed0 21", content)
        self.assertIn(
            "--out-prefix meshecho_v2_1_23_icc2027_generalization", content
        )
        self.assertIn("--protocol meshecho", content)

    def test_fixed_once_report_reproduces_schedule_and_matched_timing(self) -> None:
        args = self._fixed_once_args()
        args.matched_rreq_timing = True
        row = run_one_probe(args, "meshecho", seed=1)
        with TemporaryDirectory() as directory:
            args.csv = Path(directory) / "fixed.csv"
            report = Path(directory) / "fixed.md"
            write_report(report, [row], args)
            content = report.read_text(encoding="utf-8")

        self.assertIn("--seeds 1", content)
        self.assertIn("--seed0 1", content)
        self.assertIn("--pair-schedule fixed-once", content)
        self.assertIn("--matched-rreq-timing", content)
        self.assertIn("--pair-count 24", content)
        self.assertIn("--protocol meshecho", content)
        self.assertIn("--csv", content)
        self.assertIn("--report", content)

    def test_report_distinguishes_budgeted_variant_from_component_ablation(self) -> None:
        args = self._fixed_once_args()
        rows = [
            run_one_probe(args, protocol, seed=1)
            for protocol in ("meshecho", "meshecho-budgeted")
        ]
        with TemporaryDirectory() as directory:
            report = Path(directory) / "report.md"
            write_report(report, rows, args)
            content = report.read_text(encoding="utf-8")

        self.assertIn("budgeted variant is an optional comparator", content)
        self.assertNotIn("reported only as ablations", content)

    def test_report_identifies_ack_eviction_variant_when_run(self) -> None:
        args = self._fixed_once_args()
        rows = [
            run_one_probe(args, protocol, seed=1)
            for protocol in ("meshecho", "meshecho-ack-evict")
        ]
        with TemporaryDirectory() as directory:
            report = Path(directory) / "report.md"
            write_report(report, rows, args)
            content = report.read_text(encoding="utf-8")

        self.assertIn("ACK-timeout route-invalidation variant", content)
        self.assertNotIn("No MeshEcho component variants were run", content)


if __name__ == "__main__":
    unittest.main()
