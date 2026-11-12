from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import project_store, storage  # noqa: E402
from core.app import create_app  # noqa: E402


class ProjectApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "home"
        self.project = Path(self.tmp.name) / "project"
        self.project.mkdir()
        (self.project / "README.md").write_text("# Alpha\n\nBody.\n", encoding="utf-8")
        (self.project / "app.py").write_text("print('x')\n", encoding="utf-8")
        self.app = create_app(env={"LOOMSCI_PROFILE": "core"}, home=self.home)
        conn = storage.connect(self.home / "data" / "data.db")
        storage.ensure_agent(conn, "alice.test")
        project_store.create_project(
            conn, code="alpha", name="Alpha", sources=[{"role": "root", "path": str(self.project)}]
        )
        conn.close()
        self.app.testing = True
        self.client = self.app.test_client()
        self.headers = {"X-Loomsci-Agent": "alice.test"}

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_list_detail_stats_entries(self) -> None:
        listing = self.client.get("/v1/projects", headers=self.headers)
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.json["projects"][0]["code"], "alpha")
        detail = self.client.get("/v1/projects/alpha", headers=self.headers)
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json["project"]["name"], "Alpha")
        stats = self.client.get("/v1/projects/alpha/stats", headers=self.headers)
        self.assertEqual(stats.status_code, 200)
        self.assertGreaterEqual(stats.json["kinds"][0]["entries"], 1)
        entries = self.client.get("/v1/projects/alpha/entries?limit=1", headers=self.headers)
        self.assertEqual(entries.status_code, 200)
        self.assertEqual(entries.json["limit"], 1)
        self.assertEqual(len(entries.json["entries"]), 1)

    def test_unknown_project(self) -> None:
        response = self.client.get("/v1/projects/missing", headers=self.headers)
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
