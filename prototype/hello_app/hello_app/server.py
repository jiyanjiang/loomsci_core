"""Minimal process-contract example app."""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Handler(BaseHTTPRequestHandler):
    def _json(self, status: int, payload: dict) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
        if self.path == "/health":
            self._json(200, {
                "ok": True,
                "app": os.environ.get("LOOMSCI_APP_SLUG", "hello"),
                "version": "0.1.0",
                "token_present": bool(os.environ.get("LOOMSCI_APP_TOKEN")),
                "data_dir": os.environ.get("LOOMSCI_APP_DATA_DIR", ""),
            })
            return
        self._json(404, {"ok": False, "error": "not_found"})

    def log_message(self, *_args) -> None:
        return


def main() -> None:
    port = int(os.environ.get("LOOMSCI_APP_PORT", "0"))
    if not port:
        raise SystemExit("LOOMSCI_APP_PORT is required")
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
