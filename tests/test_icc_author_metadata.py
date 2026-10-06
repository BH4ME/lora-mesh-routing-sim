import re
import unittest
from pathlib import Path


class IccAuthorMetadataTest(unittest.TestCase):
    def test_paper_uses_confirmed_english_author_names(self) -> None:
        paper_dir = Path(__file__).resolve().parents[1] / "paper" / "icc2027"
        manuscript = (paper_dir / "icc2027_lora_mesh.tex").read_text(encoding="utf-8")

        self.assertIn(r"\IEEEauthorblockN{Zu Gao \quad Zhi Quan}", manuscript)
        self.assertIn(
            r"\IEEEauthorblockA{Shenzhen University, Shenzhen, China}",
            manuscript,
        )
        sources = (
            paper_dir / "icc2027_lora_mesh.tex",
            paper_dir / "references.bib",
            *paper_dir.glob("figures/*.tex"),
        )
        for path in sources:
            self.assertIsNone(
                re.search(r"[\u3400-\u9fff]", path.read_text(encoding="utf-8")),
                path,
            )


if __name__ == "__main__":
    unittest.main()
