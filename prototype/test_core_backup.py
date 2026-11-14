#!/usr/bin/env python3
"""Test Core v0 backup/restore API."""

from __future__ import annotations

import base64
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "core_v0"))

from server import create_app  # noqa: E402


class CoreBackupTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "home"
        self.app = create_app(self.home)
        self.app.testing = True
        self.client = self.app.test_client()
        self.headers = {"Authorization": "Bearer " + self.app.config["TOKEN"]}

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_backup_and_restore(self) -> None:
        item = self.client.post("/v1/items", headers=self.headers, json={
            "app": "report", "type": "report.note", "title": "backup",
            "body": "body", "tags": ["x"],
        }).json["item"]
        blob = self.client.post("/v1/blobs", headers=self.headers, json={
            "filename": "a.md", "content_type": "text/markdown",
            "content_base64": base64.b64encode(b"# a").decode("ascii"),
            "item_id": item["id"],
        })
        self.assertEqual(blob.status_code, 201)
        (self.home / "logs").mkdir()
        (self.home / "logs" / "core.log").write_text("log", encoding="utf-8")
        (self.home / "apps" / "demo" / "data").mkdir(parents=True)
        (self.home / "apps" / "demo" / "data" / "state.txt").write_text("state", encoding="utf-8")
        (self.home / "apps" / "demo" / "code").mkdir(parents=True)
        (self.home / "apps" / "demo" / "code" / "server.py").write_text("code", encoding="utf-8")
        created = self.client.post("/v1/backups", headers=self.headers, json={})
        self.assertEqual(created.status_code, 201, created.get_data(as_text=True))
        backup_path = Path(created.json["backup"]["path"])
        manifest = json.loads((backup_path / "manifest.json").read_text(encoding="utf-8"))
        files = {row["path"] for row in manifest["files"]}
        self.assertIn("data/core.db", files)
        self.assertIn("data/blobs/" + blob.json["blob"]["id"], files)
        self.assertIn("apps/demo/data/state.txt", files)
        self.assertFalse(any("local.token" in path or "logs/" in path or "code/" in path for path in files))
        listed = self.client.get("/v1/backups", headers=self.headers)
        self.assertEqual(len(listed.json["backups"]), 1)
        target = Path(self.tmp.name) / "restored"
        restored = self.client.post("/v1/backups/restore", headers=self.headers, json={
            "backup": str(backup_path), "target": str(target),
        })
        self.assertEqual(restored.status_code, 200, restored.get_data(as_text=True))
        conn = sqlite3.connect(target / "data" / "core.db")
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM items").fetchone()[0], 1)
        conn.close()
        self.assertTrue((target / "apps" / "demo" / "data" / "state.txt").is_file())
        self.assertTrue((target / "local.token").is_file())
        self.assertFalse((target / "apps" / "demo" / "code").exists())

    def test_restore_nonempty_rejected(self) -> None:
        created = self.client.post("/v1/backups", headers=self.headers, json={})
        target = Path(self.tmp.name) / "nonempty"
        target.mkdir()
        (target / "marker").write_text("keep", encoding="utf-8")
        response = self.client.post("/v1/backups/restore", headers=self.headers, json={
            "backup": created.json["backup"]["path"], "target": str(target),
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual((target / "marker").read_text(encoding="utf-8"), "keep")


if __name__ == "__main__":
    unittest.main()
