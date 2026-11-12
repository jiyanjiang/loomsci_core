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

    def do_PUT(self) -> None:
        _Upstream.last_path = self.path
        _Upstream.last_method = self.command
        length = int(self.headers.get("Content-Length") or 0)
        if length:
            self.rfile.read(length)
        payload = b'{"ok":true}'
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
        self.site_path = Path(self.tmp.name) / "site.json"
        self.old = (server.Handler.upstream_port, server.Handler.agent, server.Handler.site_path)
        server.Handler.upstream_port = self.upstream.server_port
        server.Handler.agent = server.default_agent(self.home)
        server.Handler.site_path = self.site_path
        self.shell = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        self.shell_thread = threading.Thread(target=self.shell.serve_forever, daemon=True)
        self.shell_thread.start()

    def tearDown(self) -> None:
        self.shell.shutdown()
        self.upstream.shutdown()
        server.Handler.upstream_port, server.Handler.agent, server.Handler.site_path = self.old
        self.tmp.cleanup()

    def test_site_config_roundtrip(self) -> None:
        url = f"http://127.0.0.1:{self.shell.server_port}/api/site"
        with urllib.request.urlopen(url) as response:
            default = json.loads(response.read())["site"]
        self.assertEqual(default["logo_url"], "https://www.loomsci.com/nav-logo.png")
        body = json.dumps({
            "site_name": "Test Site",
            "logo_url": "https://example.test/logo.png",
            "links": [{"label": "Docs", "href": "https://example.test/docs"}],
            "footer": "footer",
        }).encode()
        request = urllib.request.Request(url, data=body, method="POST", headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request) as response:
            saved = json.loads(response.read())["site"]
        self.assertEqual(saved["site_name"], "Test Site")
        self.assertTrue(self.site_path.is_file())
        with urllib.request.urlopen(url) as response:
            loaded = json.loads(response.read())["site"]
        self.assertEqual(loaded, saved)

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
        request = urllib.request.Request(
            f"http://127.0.0.1:{self.shell.server_port}/api/v1/settings/llm/deepseek/key",
            data=b'{"api_key":"x"}', method="PUT",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request) as response:
            self.assertEqual(response.status, 200)
        self.assertEqual(_Upstream.last_method, "PUT")
        with urllib.request.urlopen(f"http://127.0.0.1:{self.shell.server_port}/") as response:
            html = response.read().decode()
            self.assertIn("loomsci", html)
            self.assertIn('data-i18n="nav.posts"', html)
            self.assertIn("/i18n.js?v=0.5.5", html)
        for route in ("/app", "/app/posts", "/app/tasks", "/app/memory", "/app/inbox", "/app/site"):
            with urllib.request.urlopen(f"http://127.0.0.1:{self.shell.server_port}{route}") as response:
                self.assertEqual(response.status, 200)
                self.assertIn('data-i18n="nav.posts"', response.read().decode())
        with urllib.request.urlopen(f"http://127.0.0.1:{self.shell.server_port}/i18n.js") as response:
            script = response.read().decode()
            self.assertIn('"zh-CN"', script)
            self.assertIn('"nav.posts": "帖子"', script)


if __name__ == "__main__":
    unittest.main()
