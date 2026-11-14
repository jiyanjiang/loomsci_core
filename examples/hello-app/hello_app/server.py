"""SDK-based hello app for Core v0."""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from loomsci_core.sdk import CoreClient


class Handler(BaseHTTPRequestHandler):
    def _json(self, status: int, payload: dict) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._json(200, {"ok": True, "app": "sdk-demo", "version": "0.1.0"})
        else:
            self._json(404, {"ok": False, "error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/write":
            self._json(404, {"ok": False, "error": "not_found"})
            return
        try:
            client = CoreClient(os.environ["LOOMSCI_CORE_URL"], os.environ["LOOMSCI_APP_TOKEN"])
            item = client.create_item(
                app="sdk-demo", type="sdk-demo.note", title="from SDK app",
                body="SDK wrote this", tags=["sdk"],
            )
            self._json(201, {"ok": True, "item": item})
        except Exception as exc:
            self._json(500, {"ok": False, "error": str(exc)})

    def log_message(self, *_args) -> None:
        return


def main() -> None:
    port = int(os.environ["LOOMSCI_APP_PORT"])
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
