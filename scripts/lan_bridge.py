#!/usr/bin/env python3
"""Test-only LAN bridge for loomsci_core.

The Core host binds loopback and validates Host/Origin. This bridge listens on
a LAN interface and rewrites Host/Origin to loopback before forwarding.

WARNING: it bypasses the local boundary and has no authentication. Use only on
a trusted LAN, only during testing, and stop it afterwards.
"""

from __future__ import annotations

import argparse
import http.client
import http.server
import sys

HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}


class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    upstream_host = "127.0.0.1"
    upstream_port = 8787

    def do_GET(self) -> None:
        self._forward()

    def do_HEAD(self) -> None:
        self._forward()

    def do_POST(self) -> None:
        self._forward()

    def do_PUT(self) -> None:
        self._forward()

    def do_DELETE(self) -> None:
        self._forward()

    def do_PATCH(self) -> None:
        self._forward()

    def _forward(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else None
        headers = {
            key: value
            for key, value in self.headers.items()
            if key.lower() not in HOP_HEADERS and key.lower() not in {"host", "origin"}
        }
        headers["Host"] = f"{self.upstream_host}:{self.upstream_port}"
        origin = self.headers.get("Origin")
        if origin:
            headers["Origin"] = f"http://{self.upstream_host}:{self.upstream_port}"
        try:
            conn = http.client.HTTPConnection(
                self.upstream_host, self.upstream_port, timeout=30
            )
            conn.request(self.command, self.path, body=body, headers=headers)
            response = conn.getresponse()
            data = response.read()
            self.send_response(response.status, response.reason)
            for key, value in response.getheaders():
                if key.lower() in HOP_HEADERS or key.lower() == "content-length":
                    continue
                self.send_header(key, value)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(data)
            conn.close()
        except Exception as exc:  # noqa: BLE001
            payload = f"bridge error: {type(exc).__name__}: {exc}".encode()
            self.send_response(502)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("[lan-bridge] " + fmt % args + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--listen", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8788)
    parser.add_argument("--upstream-host", default="127.0.0.1")
    parser.add_argument("--upstream-port", type=int, default=8787)
    args = parser.parse_args()
    Handler.upstream_host = args.upstream_host
    Handler.upstream_port = args.upstream_port
    server = http.server.ThreadingHTTPServer((args.listen, args.port), Handler)
    print(
        f"LAN bridge on http://{args.listen}:{args.port} -> "
        f"http://{args.upstream_host}:{args.upstream_port}",
        flush=True,
    )
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
