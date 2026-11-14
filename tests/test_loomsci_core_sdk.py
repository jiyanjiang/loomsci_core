from __future__ import annotations

import base64
import json
import socket
import sys
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path

from werkzeug.serving import make_server

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from loomsci_core.sdk import CoreClient  # noqa: E402
from loomsci_core.server import create_app  # noqa: E402


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class SdkTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "home"
        self.port = free_port()
        self.app = create_app(self.home, core_url=f"http://127.0.0.1:{self.port}")
        self.server = make_server("127.0.0.1", self.port, self.app, threaded=True)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.client = CoreClient(f"http://127.0.0.1:{self.port}", self.app.config["TOKEN"])

    def tearDown(self) -> None:
        self.server.shutdown()
        self.tmp.cleanup()

    def test_sdk_items_tags_search_blob(self) -> None:
        self.assertTrue(self.client.health()["ok"])
        item = self.client.create_item(
            app="report", type="report.note", title="SDK",
            body="public API", tags=["sdk"],
        )
        self.assertEqual(self.client.get_item(item["id"])["title"], "SDK")
        self.assertEqual([row["id"] for row in self.client.search("public")], [item["id"]])
        blob = self.client.upload_blob(
            filename="x.md", content_type="text/markdown",
            data=b"# sdk", item_id=item["id"],
        )
        self.assertEqual(self.client.download_blob(blob["id"]), b"# sdk")
        self.client.set_tags(item["id"], ["changed"])
        self.assertEqual(self.client.list_tags()[0]["tag"], "changed")

    def test_sdk_example_app(self) -> None:
        source = ROOT / "examples" / "hello-app"
        installed = self.client._request("POST", "/v1/apps/install", {"source": str(source)})
        self.assertTrue(installed["ok"])
        started = self.client._request("POST", "/v1/apps/sdk-demo/start", {})
        self.assertTrue(started["ok"])
        try:
            request = urllib.request.Request(
                f"http://127.0.0.1:{started['port']}/write",
                data=b"{}", method="POST",
            )
            with urllib.request.urlopen(request, timeout=10) as response:
                self.assertEqual(response.status, 201)
            items = self.client.list_items(app="sdk-demo")
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0]["title"], "from SDK app")
        finally:
            self.client._request("POST", "/v1/apps/sdk-demo/stop", {})


if __name__ == "__main__":
    unittest.main()
