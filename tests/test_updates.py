from __future__ import annotations

import hashlib
import http.server
import json
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import updates  # noqa: E402


class _Handler(http.server.BaseHTTPRequestHandler):
    root = Path(".")

    def do_GET(self) -> None:
        name = self.path.lstrip("/") or "latest.json"
        path = self.root / name
        if not path.is_file():
            self.send_error(404)
            return
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *_args) -> None:
        return


class UpdatesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.home = self.root / "home"
        (self.home / "core").mkdir(parents=True)
        (self.home / "core" / "VERSION").write_text("1.0.0\n", encoding="utf-8")
        self.package = b"fake-package-bytes"
        (self.root / "release.zip").write_bytes(self.package)
        latest = {
            "version": "1.0.1",
            "url": "release.zip",
            "bytes": len(self.package),
            "sha256": hashlib.sha256(self.package).hexdigest(),
        }
        (self.root / "latest.json").write_text(json.dumps(latest), encoding="utf-8")
        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        _Handler.root = self.root
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.old = os.environ.get("LOOMSCI_UPDATE_URL")
        os.environ["LOOMSCI_UPDATE_URL"] = f"http://127.0.0.1:{self.server.server_port}/latest.json"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        if self.old is None:
            os.environ.pop("LOOMSCI_UPDATE_URL", None)
        else:
            os.environ["LOOMSCI_UPDATE_URL"] = self.old
        self.tmp.cleanup()

    def test_check_and_download(self) -> None:
        result = updates.check(self.home)
        self.assertTrue(result["available"])
        downloaded = updates.download(self.home)
        self.assertTrue(Path(downloaded["path"]).is_file())
        self.assertEqual(Path(downloaded["path"]).read_bytes(), self.package)

    def test_older_latest_is_not_available(self) -> None:
        (self.home / "core" / "VERSION").write_text("1.0.2\n", encoding="utf-8")
        result = updates.check(self.home)
        self.assertFalse(result["available"])

    def test_beta_versions_compare_numerically(self) -> None:
        self.assertLess(updates.version_key("0.1.0-beta.12"), updates.version_key("0.1.0-beta.13"))
        self.assertLess(updates.version_key("0.1.0-beta.13"), updates.version_key("0.1.0"))

    def test_sha_mismatch_is_rejected(self) -> None:
        latest = json.loads((self.root / "latest.json").read_text(encoding="utf-8"))
        latest["sha256"] = "0" * 64
        (self.root / "latest.json").write_text(json.dumps(latest), encoding="utf-8")
        updates.check(self.home)
        with self.assertRaises(updates.UpdateError):
            updates.download(self.home)
        self.assertEqual(list((self.home / "updates").glob("*.part")), [])


if __name__ == "__main__":
    unittest.main()
