from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import project_store, storage  # noqa: E402


class ProjectStoreTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "home"
        self.project = Path(self.tmp.name) / "lexicon"
        (self.project / "data").mkdir(parents=True)
        (self.project / "docs").mkdir()
        (self.project / "README.md").write_text("# Lexicon\n\nA lexicon project.\n", encoding="utf-8")
        (self.project / "scripts.py").write_text("print('x')\n", encoding="utf-8")
        (self.project / "data" / "fts.duckdb").write_bytes(b"not-a-real-db")
        (self.project / "docs" / "guide.md").write_text("# Guide\n\nBody.\n", encoding="utf-8")
        storage.init_db(self.home / "data" / "data.db")
        self.conn = storage.connect(self.home / "data" / "data.db")

    def tearDown(self) -> None:
        self.conn.close()
        self.tmp.cleanup()

    def test_register_is_reference_only_and_indexes_metadata(self) -> None:
        before = sorted(str(path) for path in self.project.rglob("*"))
        project = project_store.create_project(
            self.conn,
            code="lexicon",
            name="Lexicon",
            description="test",
            project_type="research",
            sources=[
                {"role": "code", "path": str(self.project)},
                {"role": "data", "path": str(self.project / "data")},
            ],
            app_port=5010,
        )
        after = sorted(str(path) for path in self.project.rglob("*"))
        self.assertEqual(before, after)
        self.assertEqual(project["code"], "lexicon")
        self.assertEqual(len(project["sources"]), 2)
        self.assertGreaterEqual(project["counts"]["entries"], 3)
        self.assertEqual(project["apps"][0]["port"], 5010)
        self.assertEqual(project_store.get_project(self.conn, "lexicon")["code"], "lexicon")
        self.assertEqual(len(project_store.list_projects(self.conn)), 1)

    def test_refresh_updates_entries(self) -> None:
        project_store.create_project(
            self.conn, code="alpha", name="Alpha", sources=[{"role": "root", "path": str(self.project)}]
        )
        first = project_store.get_project(self.conn, "alpha")
        (self.project / "new.md").write_text("# New\n", encoding="utf-8")
        refreshed = project_store.refresh_project(self.conn, "alpha")
        self.assertGreater(refreshed["counts"]["entries"], first["counts"]["entries"])

    def test_remove(self) -> None:
        project_store.create_project(
            self.conn, code="alpha", name="Alpha", sources=[{"role": "root", "path": str(self.project)}]
        )
        self.assertTrue(project_store.remove_project(self.conn, "alpha"))
        self.assertIsNone(project_store.get_project(self.conn, "alpha"))


if __name__ == "__main__":
    unittest.main()
