from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import projects  # noqa: E402


class ProjectScanTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "downloads"
        self.root.mkdir()
        alpha = self.root / "alpha"
        (alpha / "src").mkdir(parents=True)
        (alpha / "README.md").write_text("# Alpha\n\nA project.\n\nRun `python app.py --port 5010`.\n", encoding="utf-8")
        (alpha / "pyproject.toml").write_text("[project]\nname='alpha'\n", encoding="utf-8")
        (alpha / "src" / "app.py").write_text("print('x')\n", encoding="utf-8")
        (alpha / "node_modules").mkdir()
        (alpha / "node_modules" / "x.js").write_text("x", encoding="utf-8")
        nested = alpha / "nested"
        nested.mkdir()
        (nested / "pyproject.toml").write_text("[project]\nname='nested'\n", encoding="utf-8")

        beta = self.root / "beta"
        beta.mkdir()
        (beta / "README.md").write_text("# Beta book\n\nA book.\n", encoding="utf-8")
        (beta / "requirements.txt").write_text("x\n", encoding="utf-8")
        (beta / "snapshots_v1").mkdir()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_scan_is_read_only_and_stops_at_project_root(self) -> None:
        before = sorted(str(path) for path in self.root.rglob("*"))
        result = projects.scan(self.root, depth=3, min_score=2)
        after = sorted(str(path) for path in self.root.rglob("*"))
        self.assertEqual(before, after)
        self.assertTrue(result["read_only"])
        self.assertEqual(result["count"], 2)
        paths = {item["relative_path"] for item in result["projects"]}
        self.assertIn("alpha", paths)
        self.assertIn("beta", paths)
        self.assertNotIn("alpha/nested", paths)
        alpha = next(item for item in result["projects"] if item["relative_path"] == "alpha")
        self.assertEqual(alpha["app_port"], 5010)
        self.assertGreaterEqual(alpha["counts"]["py"], 1)
        self.assertNotIn("node_modules", str(alpha["counts"].get("db_files")))

    def test_exclude_pattern(self) -> None:
        result = projects.scan(self.root, depth=3, min_score=2, exclude=("beta*",))
        self.assertEqual([item["code"] for item in result["projects"]], ["alpha"])

    def test_missing_root(self) -> None:
        with self.assertRaises(FileNotFoundError):
            projects.scan(self.root / "missing")


if __name__ == "__main__":
    unittest.main()
