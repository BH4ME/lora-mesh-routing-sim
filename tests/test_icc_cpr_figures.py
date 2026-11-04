import csv
import json
import tempfile
import unittest
from pathlib import Path

from paper.icc2027.figures.build_cpr_figures import summarize_population


ROOT = Path(__file__).resolve().parents[1]


class IccCprFigureDataTest(unittest.TestCase):
    def test_summary_uses_equal_seed_means_and_paired_controls(self) -> None:
        prefix = ROOT / "results" / "meshecho_cpr_holdout_92300_92319_20261006"
        summary = summarize_population(
            runs_path=prefix.with_suffix(".runs.csv"),
            actions_path=prefix.with_suffix(".actions.jsonl"),
            manifest_path=prefix.with_suffix(".manifest.json"),
        )

        self.assertEqual(summary["seed_count"], 20)
        self.assertAlmostEqual(
            summary["arms"]["meshecho-cpr"]["ack"]["mean"],
            0.982890588040634,
            places=12,
        )
        self.assertAlmostEqual(
            summary["paired"]["meshecho-drc-no-rescue"]["ack"]["mean"],
            0.03337102121942513,
            places=12,
        )
        self.assertEqual(summary["actions"]["F_RECOVERY"], 21)

    def test_summary_rejects_trace_mismatch(self) -> None:
        prefix = ROOT / "results" / "meshecho_cpr_holdout_92300_92319_20261006"
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            runs = temp / "runs.csv"
            rows = list(csv.DictReader(prefix.with_suffix(".runs.csv").open()))
            rows[-1]["scheduled_trace_sha256"] = "tampered"
            with runs.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
            with self.assertRaises(ValueError):
                summarize_population(
                    runs_path=runs,
                    actions_path=prefix.with_suffix(".actions.jsonl"),
                    manifest_path=prefix.with_suffix(".manifest.json"),
                )


if __name__ == "__main__":
    unittest.main()
