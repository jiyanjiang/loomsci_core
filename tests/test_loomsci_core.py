from __future__ import annotations

import base64
import json
import socket
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from loomsci_core.server import create_app  # noqa: E402


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class FormalCoreTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "home"
        self.app = create_app(self.home)
        self.app.testing = True
        self.client = self.app.test_client()
        self.headers = {"Authorization": "Bearer " + self.app.config["TOKEN"]}

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_items_and_search(self) -> None:
        self.assertEqual(self.client.get("/v1/health").status_code, 200)
        self.assertEqual(self.client.get("/v1/items").status_code, 401)
        created = self.client.post("/v1/items", headers=self.headers, json={
            "app": "report", "type": "report.note", "title": "pkg",
            "body": "formal package", "tags": ["pkg"],
        })
        self.assertEqual(created.status_code, 201, created.get_data(as_text=True))
        item = created.json["item"]
        self.assertEqual(item["tags"][0]["tag"], "pkg")
        found = self.client.get("/v1/search?q=formal", headers=self.headers)
        self.assertEqual([row["id"] for row in found.json["items"]], [item["id"]])

    def test_ui_and_asset_routes(self) -> None:
        page = self.client.get("/")
        self.assertEqual(page.status_code, 200)
        self.assertIn("LoomSci Core", page.get_data(as_text=True))
        self.assertNotIn("__LOOMSCI_TOKEN__", page.get_data(as_text=True))
        self.assertIn("HttpOnly", page.headers.get("Set-Cookie", ""))
        self.assertIn("SameSite=Strict", page.headers.get("Set-Cookie", ""))
        self.assertEqual(self.client.get("/v1/items").status_code, 200)
        asset = self.client.get("/assets/app.js")
        self.assertEqual(asset.status_code, 200)
        self.assertIn("create-form", asset.get_data(as_text=True))
        asset.close()

    def test_item_includes_blobs(self) -> None:
        created = self.client.post("/v1/items", headers=self.headers, json={
            "app": "report", "type": "report.note", "title": "attached",
            "body": "with file",
        })
        item = created.json["item"]
        blob = self.client.post("/v1/blobs", headers=self.headers, json={
            "filename": "note.txt", "content_type": "text/plain",
            "content_base64": base64.b64encode(b"hello").decode("ascii"),
            "item_id": item["id"],
        })
        self.assertEqual(blob.status_code, 201, blob.get_data(as_text=True))
        fetched = self.client.get("/v1/items/" + item["id"], headers=self.headers)
        self.assertEqual(fetched.json["item"]["blobs"][0]["filename"], "note.txt")
        self.assertTrue(fetched.json["item"]["blobs"][0]["hash_name"].endswith(".txt"))

    def test_backup_and_restore(self) -> None:
        created = self.client.post("/v1/items", headers=self.headers, json={
            "app": "report", "type": "report.note", "title": "backup",
            "body": "portable", "tags": ["backup"],
        })
        self.assertEqual(created.status_code, 201, created.get_data(as_text=True))
        backup = self.client.post("/v1/backups", headers=self.headers)
        self.assertEqual(backup.status_code, 201, backup.get_data(as_text=True))
        verified = self.client.post("/v1/backups/verify", headers=self.headers, json={
            "backup": backup.json["backup"]["path"],
        })
        self.assertEqual(verified.status_code, 200, verified.get_data(as_text=True))
        target = Path(self.tmp.name) / "restored"
        restored = self.client.post("/v1/backups/restore", headers=self.headers, json={
            "backup": backup.json["backup"]["path"], "target": str(target),
        })
        self.assertEqual(restored.status_code, 200, restored.get_data(as_text=True))
        restored_app = create_app(target)
        restored_client = restored_app.test_client()
        headers = {"Authorization": "Bearer " + restored_app.config["TOKEN"]}
        found = restored_client.get("/v1/search?q=portable", headers=headers)
        self.assertEqual([row["title"] for row in found.json["items"]], ["backup"])

    def test_schema_version_and_migration_backup(self) -> None:
        db = self.home / "data" / "core.db"
        conn = sqlite3.connect(db)
        conn.execute("PRAGMA user_version = 0")
        conn.commit(); conn.close()
        create_app(self.home)
        conn = sqlite3.connect(db)
        self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 1)
        conn.close()
        self.assertTrue(list(db.parent.glob("core.db.pre-v1-*")))

    def test_future_schema_is_rejected(self) -> None:
        db = self.home / "data" / "core.db"
        conn = sqlite3.connect(db)
        conn.execute("PRAGMA user_version = 999")
        conn.commit(); conn.close()
        with self.assertRaises(RuntimeError):
            create_app(self.home)

    def test_module_cli_lifecycle(self) -> None:
        port = free_port()
        command = [sys.executable, "-m", "loomsci_core", "--home", str(self.home), "--port", str(port)]
        started = subprocess.run(command + ["start", "--json"], cwd=ROOT, text=True, capture_output=True)
        if started.returncode != 0:
            logs = []
            for name in ("core.stdout.log", "core.stderr.log"):
                log = self.home / "logs" / name
                logs.append(name + ":\n" + (log.read_text(encoding="utf-8", errors="replace") if log.is_file() else "<missing>"))
            self.fail((started.stderr or "") + "\n" + "\n".join(logs))
        try:
            status = subprocess.run(command + ["status", "--json"], cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(status.returncode, 0, status.stderr)
            self.assertTrue(json.loads(status.stdout)["running"])
        finally:
            subprocess.run(command + ["stop", "--json"], cwd=ROOT, text=True, capture_output=True)


if __name__ == "__main__":
    unittest.main()
