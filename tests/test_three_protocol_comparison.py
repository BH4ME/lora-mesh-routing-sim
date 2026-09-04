import csv
import tempfile
import unittest
from pathlib import Path

from tools import build_three_protocol_comparison as comparison


class ThreeProtocolComparisonTest(unittest.TestCase):
    def test_write_markdown_writes_to_docs_results_folder(self) -> None:
        data = {
            scenario.key: {
                protocol: {
                    metric: 1.0
                    for metric in comparison.METRICS
                }
                for protocol in comparison.PROTOCOLS
            }
            for scenario in comparison.SCENARIOS
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            original_docs_results = comparison.DOCS_RESULTS
            comparison.DOCS_RESULTS = Path(tmpdir) / "docs" / "results"
            try:
                out_path = comparison.write_markdown(data)
            finally:
                comparison.DOCS_RESULTS = original_docs_results

        self.assertEqual(out_path.parent.name, "results")
        self.assertEqual(out_path.parent.parent.name, "docs")

    def test_collect_rejects_missing_protocol_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "comparison.csv"
            with csv_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "protocol",
                        "unicast_pdr",
                        "total_airtime_s",
                        "collision_fail",
                    ],
                    lineterminator="\n",
                )
                writer.writeheader()
                writer.writerows(
                    [
                        {
                            "protocol": "meshtastic-like",
                            "unicast_pdr": "0.95",
                            "total_airtime_s": "1000",
                            "collision_fail": "120",
                        },
                        {
                            "protocol": "meshcore-like",
                            "unicast_pdr": "0.65",
                            "total_airtime_s": "700",
                            "collision_fail": "80",
                        },
                    ]
                )

            original_scenarios = comparison.SCENARIOS
            comparison.SCENARIOS = (
                comparison.Scenario(
                    key="missing",
                    label="Missing Smart-CALM",
                    csv_path=csv_path,
                ),
            )
            try:
                with self.assertRaisesRegex(ValueError, "smart-calm"):
                    comparison.collect()
            finally:
                comparison.SCENARIOS = original_scenarios


if __name__ == "__main__":
    unittest.main()
