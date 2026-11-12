from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import project_inspect, project_store, storage  # noqa: E402


class ProjectInspectTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "home"
        self.project = Path(self.tmp.name) / "project"
        self.project.mkdir()
        db = self.project / "data.db"
        conn = sqlite3.connect(db)
        conn.execute("CREATE TABLE papers(id INTEGER PRIMARY KEY, title TEXT, year INTEGER)")
        conn.execute("INSERT INTO papers(title, year) VALUES ('a', 2026), ('b', 2025)")
        conn.commit()
        conn.close()
        storage.init_db(self.home / "data" / "data.db")
        self.conn = storage.connect(self.home / "data" / "data.db")
        project_store.create_project(
            self.conn,
            code="alpha",
            name="Alpha",
            sources=[{"role": "root", "path": str(self.project)}],
        )

    def tearDown(self) -> None:
        self.conn.close()
        self.tmp.cleanup()

    def test_sqlite_schema_is_stored(self) -> None:
        project = project_inspect.inspect_project(self.conn, "alpha")
        self.assertEqual(len(project["schemas"]), 1)
        schema = project["schemas"][0]
        self.assertEqual(schema["engine"], "sqlite")
        self.assertIn("papers", schema["tables_json"])
        self.assertEqual(json.loads(schema["row_json"])["papers"], 2)

    def test_missing_project(self) -> None:
        with self.assertRaises(LookupError):
            project_inspect.inspect_project(self.conn, "missing")

    @unittest.skipUnless(__import__("importlib").util.find_spec("duckdb"), "duckdb not installed")
    def test_duckdb_schema(self) -> None:
        import duckdb

        path = self.project / "data.duckdb"
        conn = duckdb.connect(str(path))
        conn.execute("CREATE TABLE items(id INTEGER, name VARCHAR)")
        conn.execute("INSERT INTO items VALUES (1, 'x')")
        conn.close()
        project_store.create_project(
            self.conn, code="duck", name="Duck", sources=[{"role": "root", "path": str(self.project)}]
        )
        project = project_inspect.inspect_project(self.conn, "duck")
        self.assertTrue(any(s["engine"] == "duckdb" for s in project["schemas"]))


if __name__ == "__main__":
    unittest.main()
