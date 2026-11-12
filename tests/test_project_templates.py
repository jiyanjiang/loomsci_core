from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import project_templates  # noqa: E402


class ProjectTemplatesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.target = Path(self.tmp.name) / "book"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_create_book_template(self) -> None:
        result = project_templates.create(
            "book", self.target, code="my-book", name="My Book", description="A book"
        )
        self.assertEqual(result["code"], "my-book")
        self.assertTrue((self.target / "README.md").is_file())
        self.assertIn("My Book", (self.target / "README.md").read_text(encoding="utf-8"))
        self.assertTrue((self.target / "project.yaml").is_file())

    def test_non_empty_target_is_rejected(self) -> None:
        self.target.mkdir()
        (self.target / "keep.txt").write_text("x", encoding="utf-8")
        with self.assertRaises(ValueError):
            project_templates.create("research", self.target)
        self.assertEqual((self.target / "keep.txt").read_text(encoding="utf-8"), "x")

    def test_list_templates(self) -> None:
        names = {item["name"] for item in project_templates.list_templates()}
        self.assertEqual(names, {"book", "research", "opc"})


if __name__ == "__main__":
    unittest.main()
