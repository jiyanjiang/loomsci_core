from __future__ import annotations

import json
import sys
import tempfile
import threading
import unittest
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from addons.notify import server  # noqa: E402


class _Core(BaseHTTPRequestHandler):
    read_calls = 0

    def _send(self, payload: dict) -> None:
        data = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        if self.path.startswith("/v1/inbox"):
            return self._send({"ok": True, "inbox": [{"seq": 2, "id": "p-1", "title": "Ping", "author": "bob"}]})
        if self.path.startswith("/v1/tasks"):
            return self._send({"ok": True, "tasks": [{"id": "t-1", "title": "Work", "status": "backlog", "assigned_to": None}]})
        return self._send({"ok": True, "posts": [{"seq": 1}]})

    def do_POST(self) -> None:
        _Core.read_calls += 1
        self._send({"ok": True, "changed": 1})

    def log_message(self, *_args) -> None:
        return


class NotifyTest(unittest.TestCase):
    def setUp(self) -> None:
        _Core.read_calls = 0
        self.core = ThreadingHTTPServer(("127.0.0.1", 0), _Core)
        threading.Thread(target=self.core.serve_forever, daemon=True).start()
        self.old = (server.Handler.upstream_port, server.Handler.agent)
        server.Handler.upstream_port = self.core.server_port
        server.Handler.agent = "alice.test"
        self.shell = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        threading.Thread(target=self.shell.serve_forever, daemon=True).start()

    def tearDown(self) -> None:
        self.shell.shutdown()
        self.core.shutdown()
        server.Handler.upstream_port, server.Handler.agent = self.old

    def _get(self, path: str) -> dict:
        with urllib.request.urlopen(f"http://127.0.0.1:{self.shell.server_port}{path}") as response:
            return json.loads(response.read())

    def test_summary_digest_and_read_all(self) -> None:
        summary = self._get("/api/summary")
        self.assertEqual(summary["unread"], 1)
        self.assertEqual(summary["open_tasks"], 1)
        digest = self._get("/api/digest")
        self.assertIn("unread mentions: **1**", digest["markdown"])
        request = urllib.request.Request(
            f"http://127.0.0.1:{self.shell.server_port}/api/read-all", data=b"{}", method="POST"
        )
        with urllib.request.urlopen(request) as response:
            self.assertEqual(json.loads(response.read())["changed"], 1)
        self.assertEqual(_Core.read_calls, 1)


if __name__ == "__main__":
    unittest.main()
