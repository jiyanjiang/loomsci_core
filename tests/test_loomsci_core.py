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

    def test_module_cli_lifecycle(self) -> None:
        port = free_port()
        command = [sys.executable, "-m", "loomsci_core", "--home", str(self.home), "--port", str(port)]
        started = subprocess.run(command + ["start", "--json"], cwd=ROOT, text=True, capture_output=True)
        self.assertEqual(started.returncode, 0, started.stderr)
        try:
            status = subprocess.run(command + ["status", "--json"], cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(status.returncode, 0, status.stderr)
            self.assertTrue(json.loads(status.stdout)["running"])
        finally:
            subprocess.run(command + ["stop", "--json"], cwd=ROOT, text=True, capture_output=True)


if __name__ == "__main__":
    unittest.main()
