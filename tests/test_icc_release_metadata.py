import unittest
from pathlib import Path
import re
from unittest.mock import patch

from tools.run_icc_cache_experiment import parse_args as cache_args
from tools.run_icc_generalization_experiment import parse_args as generalization_args
from tools.run_icc_sensitivity_experiments import parse_args as sensitivity_args
from tools.run_route_conflict_experiment import parse_args as conflict_args


class IccReleaseMetadataTest(unittest.TestCase):
    def test_release_version_and_historical_runner_defaults(self) -> None:
        root = Path(__file__).resolve().parents[1]
        release_version = (root / "VERSION").read_text(encoding="utf-8").strip()
        self.assertEqual(release_version, "2.1.27")
        sim_history = (root / "docs/project-management/smart_calm_sim_versions.md").read_text(encoding="utf-8")
        self.assertIn(f"current repository release is `{release_version}`", sim_history)

        firmware_header = (root / "firmware/esp32_smart_calm/include/meshecho_config.hpp").read_text(encoding="utf-8")
        firmware_doc = (root / "docs/firmware/esp32_smart_calm.md").read_text(encoding="utf-8")
        firmware_match = re.search(
            r'kMeshEchoFirmwareVersion\s*=\s*"([^"]+)"', firmware_header
        )
        self.assertIsNotNone(firmware_match)
        self.assertIn(f"Firmware release: `{firmware_match.group(1)}`", firmware_doc)

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
