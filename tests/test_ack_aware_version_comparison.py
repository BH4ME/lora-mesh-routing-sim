import csv
import tempfile
import unittest
from pathlib import Path

from tools import build_ack_aware_version_comparison as comparison


class AckAwareVersionComparisonTest(unittest.TestCase):
    def test_collect_accepts_archived_rows_without_ack_metric(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            previous_path = root / "smart_calm_v1_1_50n_mixed.csv"
            ack_path = root / "smart_calm_v1_1_ack_50n_mixed.csv"
            with previous_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "protocol",
                        "unicast_pdr",
                        "total_airtime_s",
                        "collision_fail",
                        "fallback_forward_count",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "protocol": "smart-calm",
                        "unicast_pdr": "0.90",
                        "total_airtime_s": "100",
                        "collision_fail": "10",
                        "fallback_forward_count": "5",
                    }
                )
            with ack_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "protocol",
                        "unicast_pdr",
                        "total_airtime_s",
                        "collision_fail",
                        "fallback_forward_count",
                        "ack_tx",
                    ],
                    lineterminator="\n",
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "protocol": "smart-calm",
                        "unicast_pdr": "0.95",
                        "total_airtime_s": "110",
                        "collision_fail": "11",
                        "fallback_forward_count": "4",
                        "ack_tx": "8",
                    }
                )

            original_scenarios = comparison.SCENARIOS
            original_runs = comparison.RUNS
            comparison.SCENARIOS = (
                comparison.Scenario("mixed", "Mixed traffic", "50n_mixed"),
            )
            comparison.RUNS = (
                comparison.RunSpec(
                    "v1_1_previous",
                    "v1.1 previous",
                    root,
                    "smart_calm_v1_1",
                    False,
                ),
                comparison.RunSpec(
                    "v1_1_ack",
                    "v1.1 ACK-aware",
                    root,
                    "smart_calm_v1_1_ack",
                    True,
                ),
            )
            try:
                data = comparison.collect()
            finally:
                comparison.SCENARIOS = original_scenarios
                comparison.RUNS = original_runs

        self.assertIsNone(data["mixed"]["v1_1_previous"]["ack_tx"])
        self.assertEqual(data["mixed"]["v1_1_ack"]["ack_tx"], 8.0)


if __name__ == "__main__":
    unittest.main()
