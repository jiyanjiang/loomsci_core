from __future__ import annotations

import json
import sys
import tempfile
import threading
import unittest.mock
import unittest
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from addons.ui_shell import server  # noqa: E402


class _Upstream(BaseHTTPRequestHandler):
    last_path = ""

    def do_GET(self) -> None:
        _Upstream.last_path = self.path
        payload = json.dumps({"ok": True, "agent": self.headers.get("X-Loomsci-Agent")}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *_args) -> None:
        return


class UiShellTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "home"
        (self.home / "agents" / "alice").mkdir(parents=True)
        (self.home / "agents" / "alice" / "agent.json").write_text(
            json.dumps({"handle": "alice.test"}), encoding="utf-8"
        )
        self.upstream = ThreadingHTTPServer(("127.0.0.1", 0), _Upstream)
        self.thread = threading.Thread(target=self.upstream.serve_forever, daemon=True)
        self.thread.start()
        self.old = (server.Handler.upstream_port, server.Handler.agent)
        server.Handler.upstream_port = self.upstream.server_port
        server.Handler.agent = server.default_agent(self.home)
        self.shell = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        self.shell_thread = threading.Thread(target=self.shell.serve_forever, daemon=True)
        self.shell_thread.start()

    def tearDown(self) -> None:
        self.shell.shutdown()
        self.upstream.shutdown()
        server.Handler.upstream_port, server.Handler.agent = self.old
        self.tmp.cleanup()

    def test_server_bind_does_not_reverse_dns(self) -> None:
        with unittest.mock.patch("socket.getfqdn", side_effect=RuntimeError("no dns")):
            server_obj = server._LocalServer(("127.0.0.1", 0), server.Handler)
            server_obj.server_close()

    def test_default_agent_and_proxy(self) -> None:
        self.assertEqual(server.default_agent(self.home), "alice.test")
        with urllib.request.urlopen(f"http://127.0.0.1:{self.shell.server_port}/api/health") as response:
            self.assertEqual(json.loads(response.read())["addon"], "ui-shell")
        with urllib.request.urlopen(f"http://127.0.0.1:{self.shell.server_port}/api/v1/health") as response:
            payload = json.loads(response.read())
        self.assertEqual(payload["agent"], "alice.test")
        with urllib.request.urlopen(f"http://127.0.0.1:{self.shell.server_port}/api/v1/health?probe=1") as response:
            response.read()
        self.assertEqual(_Upstream.last_path, "/v1/health?probe=1")
        with urllib.request.urlopen(f"http://127.0.0.1:{self.shell.server_port}/") as response:
            html = response.read().decode()
            self.assertIn("loomsci", html)
            self.assertIn('data-i18n="nav.posts"', html)
            self.assertIn("/i18n.js?v=0.4.0", html)
        with urllib.request.urlopen(f"http://127.0.0.1:{self.shell.server_port}/i18n.js") as response:
            script = response.read().decode()
            self.assertIn('"zh-CN"', script)
            self.assertIn('"nav.posts": "帖子"', script)


if __name__ == "__main__":
    unittest.main()
