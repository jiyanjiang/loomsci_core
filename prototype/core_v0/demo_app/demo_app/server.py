"""Demo app for the Core v0 App Host."""

from __future__ import annotations

import json
import os
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def call_core(item: dict) -> dict:
    core = os.environ["LOOMSCI_CORE_URL"].rstrip("/")
    token = os.environ["LOOMSCI_APP_TOKEN"]
    data = json.dumps(item, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        core + "/v1/items", data=data, method="POST",
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.loads(response.read())


class Handler(BaseHTTPRequestHandler):
    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._json(200, {"ok": True, "app": "demo", "version": "0.1.0"})
        else:
            self._json(404, {"ok": False, "error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/write":
            self._json(404, {"ok": False, "error": "not_found"})
            return
        try:
            item = call_core({
                "app": "demo", "type": "demo.note",
                "title": "from demo app", "body": "app wrote this",
                "tags": ["demo"],
            })
            self._json(201, item)
        except Exception as exc:
            self._json(500, {"ok": False, "error": str(exc)})

    def log_message(self, *_args) -> None:
        return


def main() -> None:
    port = int(os.environ["LOOMSCI_APP_PORT"])
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
