import unittest
import csv
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory

from paper.icc2027.figures.plot_baseline_delivery import (
    render_figure,
    summarize_csv,
    write_source_data,
)


ROOT = Path(__file__).resolve().parents[1]


class IccDeliveryFigureTest(unittest.TestCase):
    def test_recurring_figure_uses_only_three_protocol_models(self) -> None:
        summary = summarize_csv(
            ROOT / "results/meshecho_v2_1_25_icc2027_baseline_feedback_fading.csv"
        )

        self.assertEqual(
            set(summary),
            {"meshecho-calibrated", "meshtastic-like", "meshcore-like"},
        )
        self.assertTrue(all(item["n"] == 20 for item in summary.values()))
        self.assertEqual(round(summary["meshecho-calibrated"]["ack_mean"], 3), 0.624)
        self.assertEqual(round(summary["meshtastic-like"]["ack_mean"], 3), 0.505)
        self.assertEqual(round(summary["meshcore-like"]["ack_mean"], 3), 0.410)
        self.assertEqual(
            round(summary["meshtastic-like"]["destination_mean"], 3), 0.989
        )

    def test_source_data_keeps_both_workloads_and_excludes_score_control(self) -> None:
        recurring = summarize_csv(
            ROOT / "results/meshecho_v2_1_25_icc2027_baseline_feedback_fading.csv"
        )
        random = summarize_csv(
            ROOT / "results/meshecho_v2_1_25_icc2027_random_sparse_fading_2001_2020.csv"
        )
        with TemporaryDirectory() as temporary:
            source_path = Path(temporary) / "source.csv"
            write_source_data(source_path, recurring, random)
            with source_path.open(newline="", encoding="utf-8") as stream:
                rows = list(csv.DictReader(stream))

        self.assertEqual(len(rows), 6)
        self.assertEqual({row["n"] for row in rows}, {"20"})
        self.assertEqual({row["workload"] for row in rows}, {"Recurring", "Random"})
        random_meshtastic = next(
            row for row in rows
            if row["workload"] == "Random" and row["protocol"] == "meshtastic-like"
        )
        self.assertEqual(round(float(random_meshtastic["ack_mean"]), 3), 0.708)
        self.assertEqual(
            round(float(random_meshtastic["destination_mean"]), 3), 0.995
        )

    @unittest.skipUnless(importlib.util.find_spec("matplotlib"), "matplotlib unavailable")
    def test_render_exports_vector_figure_and_source_data(self) -> None:
        with TemporaryDirectory() as temporary:
            output_prefix = Path(temporary) / "delivery"
            render_figure(
                ROOT / "results/meshecho_v2_1_25_icc2027_baseline_feedback_fading.csv",
                ROOT / "results/meshecho_v2_1_25_icc2027_random_sparse_fading_2001_2020.csv",
                output_prefix,
            )
            self.assertTrue(output_prefix.with_suffix(".pdf").read_bytes().startswith(b"%PDF"))
            svg = output_prefix.with_suffix(".svg").read_text(encoding="utf-8")
            self.assertIn("Meshtastic-like", svg)
            self.assertIn("MeshEcho (calibrated)", svg)
            self.assertTrue(all(line == line.rstrip() for line in svg.splitlines()))
            self.assertNotIn(
                b"\r\n",
                (output_prefix.parent / "delivery_source.csv").read_bytes(),
            )
            self.assertEqual(
                len((output_prefix.parent / "delivery_source.csv").read_text().splitlines()),
                7,
            )


if __name__ == "__main__":
    unittest.main()
