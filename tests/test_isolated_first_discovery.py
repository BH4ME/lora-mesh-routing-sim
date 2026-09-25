import csv
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from tools.run_isolated_first_discovery import (
    ExperimentConfig,
    main,
    render_report,
    run_seed,
)


class IsolatedFirstDiscoveryTest(unittest.TestCase):
    def test_each_selected_pair_gets_four_isolated_first_discoveries(self) -> None:
        rows = run_seed(1, ExperimentConfig(pair_count=2))

        self.assertEqual(len(rows), 8)
        by_pair = {}
        for row in rows:
            by_pair.setdefault(row["pair_index"], []).append(row)
            self.assertEqual(row["matched_rreq_timing"], 1)
            self.assertEqual(row["unicast_flows"], 1)
            self.assertEqual(row["route_cache_hits"], 0)
            self.assertEqual(row["discovery_count"], 1)
            candidates = json.loads(row["candidate_paths_json"])
            selected = json.loads(row["selected_path_json"])
            self.assertTrue(selected is None or selected in candidates)

        self.assertEqual(len(by_pair), 2)
        for pair_rows in by_pair.values():
            self.assertEqual(
                {row["protocol"] for row in pair_rows},
                {"meshecho", "etx-mesh", "minhop-mesh", "meshcore-like"},
            )
            self.assertEqual(len({row["source"] for row in pair_rows}), 1)
            self.assertEqual(len({row["destination"] for row in pair_rows}), 1)
            self.assertEqual(
                len({row["candidate_sets_identical"] for row in pair_rows}), 1
            )

    def test_report_flags_candidate_set_mismatch_from_raw_paths(self) -> None:
        rows = run_seed(1, ExperimentConfig(pair_count=1))
        rows[0]["candidate_paths_json"] = "[[999, 1000]]"

        report = render_report(rows, ExperimentConfig(pair_count=1))

        self.assertIn("0/1 pairs had identical candidate sets", report)
        self.assertIn("cannot attribute outcome differences solely to route ranking", report)
        self.assertIn("seed 1, pair 1", report)
        self.assertIn("## Seed-Paired Differences", report)
        self.assertIn("## Selected-Path Attribution Check", report)
        self.assertIn("Same-path outcome mismatches", report)

    def test_cli_writes_complete_one_seed_artifacts(self) -> None:
        with TemporaryDirectory() as temporary_dir:
            csv_path = Path(temporary_dir) / "isolated.csv"
            report_path = Path(temporary_dir) / "isolated.md"
            main(
                [
                    "--seeds",
                    "1",
                    "--seed0",
                    "1",
                    "--csv",
                    str(csv_path),
                    "--report",
                    str(report_path),
                ]
            )

            with csv_path.open(newline="", encoding="utf-8") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), 24 * 4)
            self.assertEqual(len({row["pair_index"] for row in rows}), 24)
            self.assertEqual(csv_path.read_bytes().count(b"\r"), 0)
            self.assertIn("24 pairs", report_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
