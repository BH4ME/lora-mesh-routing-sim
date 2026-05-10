import csv
import tempfile
import unittest
from pathlib import Path

from tools import build_three_protocol_comparison as comparison


class ThreeProtocolComparisonTest(unittest.TestCase):
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
