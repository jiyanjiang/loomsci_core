from __future__ import annotations

import json
import socket
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import addon_runtime, addons  # noqa: E402


def _manifest(name: str, *, version: str = "1.0.0", port: int = 0, requires: list[str] | None = None) -> dict:
    return {
        "name": name,
        "version": version,
        "api": "core/1",
        "requires": requires or ["core/1"],
        "routes": ["/"],
        "storage": f"addon.{name}",
        "jobs": [],
        "nav": [],
        "preserve": [],
        "package": name.replace("-", "_"),
        "entry": "server",
        "port": port,
        "health": "/health",
    }


class AddonHostTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "home"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_available_install_remove_profile(self) -> None:
        entries = {item["name"]: item for item in addons.available()}
        names = list(entries)
        self.assertIn("ui-shell", names)
        for item in entries.values():
            self.assertEqual(item["health"], "/api/health")
        result = addons.install(self.home, "ui-shell")
        self.assertTrue((self.home / "packs" / "ui_shell" / "manifest.json").is_file())
        self.assertIn("ui-shell", addons.installed(self.home))
        self.assertEqual(result["name"], "ui-shell")
        self.assertEqual(result["package"], "ui_shell")
        self.assertEqual(addons.record(self.home, "ui-shell")["version"], "0.5.3")
        data = self.home / "packs" / "ui_shell" / "data"
        data.mkdir()
        (data / "state.json").write_text("{}")
        addons.install(self.home, "ui-shell")
        self.assertTrue((data / "state.json").is_file())
        addons.update(self.home, "ui-shell")
        self.assertTrue((data / "state.json").is_file())
        self.assertTrue(addons.verify(self.home)["ok"])
        addons.remove(self.home, "ui-shell")
        self.assertTrue((data / "state.json").is_file())
        self.assertNotIn("ui-shell", addons.installed(self.home))
        installed = addons.install_profile(self.home, "personal")
        self.assertEqual([item["name"] for item in installed], ["ui-shell", "notify"])
        with self.assertRaises(addons.AddonError):
            addons.install(self.home, "missing")

    def test_install_requires_addon_dependency(self) -> None:
        bundled = Path(self.tmp.name) / "bundled"
        for name, requires in (("a", ["core/1"]), ("b", ["core/1", "a>=1.0.0"])):
            source = bundled / name
            source.mkdir(parents=True)
            (source / "server.py").write_text("")
            (source / "manifest.json").write_text(json.dumps(_manifest(name, requires=requires)))
        with mock.patch.object(addons, "BUNDLED", bundled):
            with self.assertRaises(addons.AddonError):
                addons.install(self.home, "b")
            addons.install(self.home, "a")
            addons.install(self.home, "b")
            self.assertEqual(addons.installed(self.home), ["a", "b"])

    def test_runtime_start_health_and_stop(self) -> None:
        bundled = Path(self.tmp.name) / "bundled"
        source = bundled / "demo"
        source.mkdir(parents=True)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        sock.close()
        (source / "manifest.json").write_text(json.dumps(_manifest("demo", port=port)))
        (source / "__init__.py").write_text("")
        (source / "server.py").write_text(
            "import argparse, json, socketserver\n"
            "from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer\n"
            "class S(ThreadingHTTPServer):\n"
            "    def server_bind(self):\n"
            "        socketserver.TCPServer.server_bind(self)\n"
            "        host, port = self.server_address[:2]\n"
            "        self.server_name = host\n"
            "        self.server_port = port\n"
            "class H(BaseHTTPRequestHandler):\n"
            "    def do_GET(self):\n"
            "        data = json.dumps({'ok': True}).encode()\n"
            "        self.send_response(200)\n"
            "        self.send_header('Content-Type', 'application/json')\n"
            "        self.send_header('Content-Length', str(len(data)))\n"
            "        self.end_headers()\n"
            "        self.wfile.write(data)\n"
            "    def log_message(self, *args):\n"
            "        pass\n"
            "p = argparse.ArgumentParser()\n"
            "p.add_argument('--port', type=int, default=0)\n"
            "p.add_argument('--home')\n"
            "a = p.parse_args()\n"
            "S(('127.0.0.1', a.port), H).serve_forever()\n"
        )
        with mock.patch.object(addons, "BUNDLED", bundled):
            addons.install(self.home, "demo")
            started = addon_runtime.start(self.home, "demo", timeout=30)
            self.assertTrue(started["running"])
            self.assertTrue(started["healthy"])
            self.assertEqual(addon_runtime.status(self.home, "demo")["state"], "running")
            stopped = addon_runtime.stop(self.home, "demo")
            self.assertTrue(stopped["stopped"])
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline and addon_runtime.status(self.home, "demo")["running"]:
                time.sleep(0.1)
            self.assertFalse(addon_runtime.status(self.home, "demo")["running"])


if __name__ == "__main__":
    unittest.main()
