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

from addons.collab import server  # noqa: E402


class _Core(BaseHTTPRequestHandler):
    posts: list[dict] = []

    def _send(self, status: int, payload: dict) -> None:
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        if self.path.startswith("/v1/health"):
            return self._send(200, {"ok": True, "version": "test"})
        return self._send(200, {"ok": True, "posts": self.posts})

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        payload = json.loads(self.rfile.read(length) or b"{}")
        payload["author"] = self.headers.get("X-Loomsci-Agent")
        self.posts.append(payload)
        self._send(201, {"ok": True, "post": payload})

    def log_message(self, *_args) -> None:
        return


class CollabTest(unittest.TestCase):
    def setUp(self) -> None:
        _Core.posts = []
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "home"
        self.core = ThreadingHTTPServer(("127.0.0.1", 0), _Core)
        threading.Thread(target=self.core.serve_forever, daemon=True).start()
        self.old = (server.Handler.upstream_port, server.Handler.agent, server.Handler.db_path)
        server.Handler.upstream_port = self.core.server_port
        server.Handler.agent = "alice.test"
        server.Handler.db_path = self.home / "packs" / "collab" / "data" / "collab.db"
        self.shell = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        threading.Thread(target=self.shell.serve_forever, daemon=True).start()

    def tearDown(self) -> None:
        self.shell.shutdown()
        self.core.shutdown()
        server.Handler.upstream_port, server.Handler.agent, server.Handler.db_path = self.old
        self.tmp.cleanup()

    def _request(self, method: str, path: str, payload: dict | None = None) -> dict:
        data = json.dumps(payload).encode() if payload is not None else None
        headers = {"Content-Type": "application/json"} if data else {}
        request = urllib.request.Request(
            f"http://127.0.0.1:{self.shell.server_port}{path}",
            data=data,
            headers=headers,
            method=method,
        )
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read())

    def test_room_and_thread(self) -> None:
        room = self._request("POST", "/api/rooms", {"name": "Room"})["room"]
        self.assertEqual(self._request("GET", "/api/rooms")["rooms"][0]["id"], room["id"])
        posted = self._request(
            "POST", f"/api/rooms/{room['id']}/posts", {"body": "hello"}
        )
        self.assertEqual(posted["post"]["author"], "alice.test")
        self.assertEqual(_Core.posts[0]["thread_id"], f"room:{room['id']}")
        self.assertEqual(
            self._request("GET", f"/api/rooms/{room['id']}/posts")["posts"][0]["body"],
            "hello",
        )


if __name__ == "__main__":
    unittest.main()
