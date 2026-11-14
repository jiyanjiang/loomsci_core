from __future__ import annotations

import json
import socket
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

    def test_backup_and_restore(self) -> None:
        created = self.client.post("/v1/items", headers=self.headers, json={
            "app": "report", "type": "report.note", "title": "backup",
            "body": "portable", "tags": ["backup"],
        })
        self.assertEqual(created.status_code, 201, created.get_data(as_text=True))
        backup = self.client.post("/v1/backups", headers=self.headers)
        self.assertEqual(backup.status_code, 201, backup.get_data(as_text=True))
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

    def test_module_cli_lifecycle(self) -> None:
        port = free_port()
        command = [sys.executable, "-m", "loomsci_core", "--home", str(self.home), "--port", str(port)]
        started = subprocess.run(command + ["start", "--json"], cwd=ROOT, text=True, capture_output=True)
        if started.returncode != 0:
            log = self.home / "logs" / "core.stderr.log"
            detail = log.read_text(encoding="utf-8", errors="replace") if log.is_file() else ""
            self.fail((started.stderr or "") + "\n" + detail)
        try:
            status = subprocess.run(command + ["status", "--json"], cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(status.returncode, 0, status.stderr)
            self.assertTrue(json.loads(status.stdout)["running"])
        finally:
            subprocess.run(command + ["stop", "--json"], cwd=ROOT, text=True, capture_output=True)


if __name__ == "__main__":
    unittest.main()
