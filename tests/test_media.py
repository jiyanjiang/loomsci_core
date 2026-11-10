from __future__ import annotations

import base64
import json
import shutil
import sys
import tempfile
import threading
import unittest
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from addons.media import server  # noqa: E402


PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAQAAAAECAIAAAAmkwkpAAAACXBIWXMAAAABAAAAAQBPJcTWAAAAEElEQVR4nGP8w4AALAxEcQAz1AEKG5dMywAAAABJRU5ErkJggg==")


class _Core(BaseHTTPRequestHandler):
    def _send(self, payload: dict) -> None:
        data = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        if self.path.startswith("/v1/status"):
            return self._send({"ok": True, "last_seq": 1})
        if self.path.startswith("/v1/posts"):
            return self._send({"ok": True, "posts": [{"seq": 1, "id": "p-1", "author": "alice", "created_at": "now", "attachments": [
                {"id": "a-img", "filename": "x.png", "content_type": "image/png", "bytes": 3},
                {"id": "a-aud", "filename": "x.mp3", "content_type": "audio/mpeg", "bytes": 4},
                {"id": "a-vid", "filename": "x.mp4", "content_type": "video/mp4", "bytes": 5},
                {"id": "a-bin", "filename": "x.bin", "content_type": "application/octet-stream", "bytes": 6},
            ]}]})
        data = PNG
        self.send_response(200)
        self.send_header("Content-Type", "image/png")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *_args) -> None:
        return


class MediaTest(unittest.TestCase):
    def setUp(self) -> None:
        self.core = ThreadingHTTPServer(("127.0.0.1", 0), _Core)
        threading.Thread(target=self.core.serve_forever, daemon=True).start()
        self.tmp = tempfile.TemporaryDirectory()
        self.old = (server.Handler.upstream_port, server.Handler.agent, server.Handler.thumb_dir)
        server.Handler.upstream_port = self.core.server_port
        server.Handler.agent = "alice.test"
        server.Handler.thumb_dir = Path(self.tmp.name) / "thumbs"
        self.shell = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        threading.Thread(target=self.shell.serve_forever, daemon=True).start()

    def tearDown(self) -> None:
        self.shell.shutdown()
        self.core.shutdown()
        server.Handler.upstream_port, server.Handler.agent, server.Handler.thumb_dir = self.old
        self.tmp.cleanup()

    def test_library_and_attachment(self) -> None:
        with urllib.request.urlopen(f"http://127.0.0.1:{self.shell.server_port}/api/library") as response:
            data = json.loads(response.read())
        self.assertEqual(data["counts"], {"image": 1, "audio": 1, "video": 1, "file": 1})
        self.assertEqual(data["items"][0]["kind"], "image")
        with urllib.request.urlopen(f"http://127.0.0.1:{self.shell.server_port}/api/attachment/a-img") as response:
            self.assertEqual(response.read(), PNG)

    @unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg unavailable")
    def test_thumbnail(self) -> None:
        with urllib.request.urlopen(f"http://127.0.0.1:{self.shell.server_port}/api/thumbnail/a-img") as response:
            self.assertEqual(response.headers.get("Content-Type"), "image/jpeg")
            self.assertGreater(len(response.read()), 0)


if __name__ == "__main__":
    unittest.main()
