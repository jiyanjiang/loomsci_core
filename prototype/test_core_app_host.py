#!/usr/bin/env python3
"""Test Core v0 App Host + scoped app tokens."""

from __future__ import annotations

import json
import socket
import sys
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path

from werkzeug.serving import make_server

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "core_v0"))

from server import create_app  # noqa: E402


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class CoreAppHostTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "home"
        self.port = free_port()
        self.app = create_app(self.home, core_url=f"http://127.0.0.1:{self.port}")
        self.server = make_server("127.0.0.1", self.port, self.app, threaded=True)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.client = self.app.test_client()
        self.master = {"Authorization": "Bearer " + self.app.config["TOKEN"]}

    def tearDown(self) -> None:
        self.server.shutdown()
        self.tmp.cleanup()

    def test_app_host_and_scope(self) -> None:
        source = ROOT / "core_v0" / "demo_app"
        installed = self.client.post("/v1/apps/install", headers=self.master, json={"source": str(source)})
        self.assertEqual(installed.status_code, 201, installed.get_data(as_text=True))
        started = self.client.post("/v1/apps/demo/start", headers=self.master, json={})
        self.assertEqual(started.status_code, 200, started.get_data(as_text=True))
        app_port = started.json["port"]
        request = urllib.request.Request(f"http://127.0.0.1:{app_port}/write", data=b"{}", method="POST")
        with urllib.request.urlopen(request, timeout=10) as response:
            written = json.loads(response.read())
        self.assertEqual(written["item"]["app"], "demo")
        items = self.client.get("/v1/items?app=demo", headers=self.master).json["items"]
        self.assertEqual(len(items), 1)
        host = self.app.config["HOST"]
        app_token = next(iter(host.tokens))
        scoped = {"Authorization": "Bearer " + app_token}
        self.assertEqual([row["app"] for row in self.client.get("/v1/items", headers=scoped).json["items"]], ["demo"])
        forbidden = self.client.post("/v1/items", headers=scoped, json={
            "app": "report", "type": "report.note", "body": "escape",
        })
        self.assertEqual(forbidden.status_code, 403)
        master_item = self.client.post("/v1/items", headers=self.master, json={
            "app": "report", "type": "report.note", "body": "private",
        }).json["item"]
        self.assertEqual(self.client.get(f"/v1/items/{master_item['id']}", headers=scoped).status_code, 404)
        marker = self.home / "apps" / "demo" / "data" / "marker.txt"
        marker.write_text("keep", encoding="utf-8")
        updated = self.client.post("/v1/apps/demo/update", headers=self.master, json={"source": str(source)})
        self.assertEqual(updated.status_code, 200, updated.get_data(as_text=True))
        self.assertEqual(marker.read_text(encoding="utf-8"), "keep")
        stopped = self.client.post("/v1/apps/demo/stop", headers=self.master, json={})
        self.assertEqual(stopped.status_code, 200)
        removed = self.client.delete("/v1/apps/demo", headers=self.master)
        self.assertEqual(removed.status_code, 200)
        self.assertTrue(Path(removed.json["data"]).is_dir())


if __name__ == "__main__":
    unittest.main()
