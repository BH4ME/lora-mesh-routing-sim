import unittest

from analyze_results import aggregate, confidence_interval_95


class AnalyzeResultsTest(unittest.TestCase):
    def test_confidence_interval_uses_sample_variance(self) -> None:
        mean_value, half_width = confidence_interval_95([1.0, 2.0, 3.0])

        self.assertEqual(mean_value, 2.0)
        self.assertGreater(half_width, 0.0)

    def test_aggregate_skips_metrics_missing_from_archived_csv(self) -> None:
        rows = [
            {
                "protocol": "legacy",
                "unicast_pdr": "0.8",
                "total_airtime_s": "10",
            },
            {
                "protocol": "legacy",
                "unicast_pdr": "0.9",
                "total_airtime_s": "12",
            },
        ]

        summary = aggregate({"legacy": rows})
        summary_by_metric = {row["metric"]: row for row in summary}

        self.assertEqual(summary_by_metric["unicast_pdr"]["n"], 2)
        self.assertAlmostEqual(summary_by_metric["unicast_pdr"]["mean"], 0.85)
        self.assertIn("ci95_low", summary_by_metric["total_airtime_s"])
        self.assertNotIn("channel_busy_ratio", summary_by_metric)


if __name__ == "__main__":
    unittest.main()
