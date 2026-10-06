import unittest
from pathlib import Path
from unittest.mock import patch

from tools.run_icc_cache_experiment import parse_args as cache_args
from tools.run_icc_generalization_experiment import parse_args as generalization_args
from tools.run_icc_sensitivity_experiments import parse_args as sensitivity_args
from tools.run_route_conflict_experiment import parse_args as conflict_args


class IccReleaseMetadataTest(unittest.TestCase):
    def test_release_version_and_historical_runner_defaults(self) -> None:
        root = Path(__file__).resolve().parents[1]
        self.assertEqual((root / "VERSION").read_text(encoding="utf-8").strip(), "2.1.27")

        with patch("sys.argv", ["runner"]):
            # These runners reproduce the archived 2.1.26 protocol-family
            # matrix; CPR has its own contract and artifact prefix.
            self.assertEqual(
                sensitivity_args().out_prefix,
                "meshecho_v2_1_26_icc2027_sensitivity",
            )
            self.assertEqual(
                cache_args().out_prefix,
                "meshecho_v2_1_26_icc2027_cache",
            )
            self.assertEqual(
                generalization_args().out_prefix,
                "meshecho_v2_1_26_icc2027_generalization",
            )
            self.assertEqual(
                conflict_args().csv,
                Path("results/meshecho_v2_1_26_icc2027_route_conflict.csv"),
            )


if __name__ == "__main__":
    unittest.main()
