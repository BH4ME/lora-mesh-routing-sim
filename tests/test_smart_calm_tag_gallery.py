import tempfile
import unittest
from pathlib import Path

from tools import build_smart_calm_tag_gallery as gallery


class SmartCalmTagGalleryTest(unittest.TestCase):
    def test_configured_versions_have_expected_tags_and_csvs(self) -> None:
        tags = [version.tag for version in gallery.VERSIONS]

        self.assertEqual(
            tags,
            [
                "smart-calm-sim-v1.0",
                "smart-calm-sim-v1.1",
                "smart-calm-sim-v2",
            ],
        )
        self.assertEqual(gallery.VERSIONS[-1].key, "v2")
        self.assertEqual(gallery.VERSIONS[-1].label, "v2")
        for version in gallery.VERSIONS:
            for scenario in gallery.SCENARIOS:
                self.assertTrue(
                    version.csv_path(scenario).exists(),
                    f"missing CSV for {version.tag} / {scenario.key}",
                )

    def test_write_markdown_links_each_version_chart(self) -> None:
        fake_outputs = {
            version.key: {
                metric: Path("results") / "figures" / "smart_calm_tags" / f"{version.key}_{metric}.svg"
                for metric in gallery.METRICS
            }
            for version in gallery.VERSIONS
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            original_docs_results = gallery.DOCS_RESULTS
            gallery.DOCS_RESULTS = Path(tmpdir) / "docs" / "results"
            try:
                out_path = gallery.write_markdown(gallery.collect(), fake_outputs)
                content = out_path.read_text(encoding="utf-8")
            finally:
                gallery.DOCS_RESULTS = original_docs_results

        for version in gallery.VERSIONS:
            self.assertIn(version.tag, content)
            self.assertIn(f"{version.key}_unicast_pdr.svg", content)
            self.assertIn(f"{version.key}_total_airtime_s.svg", content)
            self.assertIn(f"{version.key}_collision_fail.svg", content)
        self.assertIn("| Tag | Commit / ref | Version focus |", content)
        self.assertIn("`release tag`", content)


if __name__ == "__main__":
    unittest.main()
