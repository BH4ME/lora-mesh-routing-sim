import unittest
from pathlib import Path
from unittest.mock import patch

from tools.run_icc_cache_experiment import parse_args as cache_args
from tools.run_icc_generalization_experiment import parse_args as generalization_args
from tools.run_icc_sensitivity_experiments import parse_args as sensitivity_args
from tools.run_route_conflict_experiment import parse_args as conflict_args


class IccReleaseMetadataTest(unittest.TestCase):
    def test_current_release_defaults_use_version_2_1_23(self) -> None:
        root = Path(__file__).resolve().parents[1]
        self.assertEqual((root / "VERSION").read_text(encoding="utf-8").strip(), "2.1.23")

        with patch("sys.argv", ["runner"]):
            self.assertEqual(
                sensitivity_args().out_prefix,
                "meshecho_v2_1_23_icc2027_sensitivity",
            )
            self.assertEqual(
                cache_args().out_prefix,
                "meshecho_v2_1_23_icc2027_cache",
            )
            self.assertEqual(
                generalization_args().out_prefix,
                "meshecho_v2_1_23_icc2027_generalization",
            )
            self.assertEqual(
                conflict_args().csv,
                Path("results/meshecho_v2_1_23_icc2027_route_conflict.csv"),
            )


if __name__ == "__main__":
    unittest.main()
