"""Standalone UI-shell add-on.

Serves a static shell and proxies /api/* to the local Core host, injecting the
default agent header. Core is not imported; the shell only consumes /v1.
"""

from __future__ import annotations

import argparse
import socketserver
import http.client
import json
import mimetypes
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"
DEFAULT_SITE = {
    "site_name": "loomsci",
    "logo_url": "https://www.loomsci.com/nav-logo.png",
    "links": [],
    "footer": "",
}


def default_agent(home: Path | None = None) -> str:
    candidates = []
    if home:
        candidates.append(home)
    env_home = os.environ.get("LOOMSCI_HOME")
    if env_home:
        candidates.append(Path(env_home).expanduser())
    candidates.append(Path.home() / ".loomsci")
    candidates.append(ROOT.parents[2])
    for base in candidates:
        path = base / "agents" / "alice" / "agent.json"
        if path.is_file():
            try:
                return str(json.loads(path.read_text(encoding="utf-8"))["handle"])
            except (OSError, ValueError, KeyError):
                pass
    return "alice.owner"


class _LocalServer(ThreadingHTTPServer):
    """Avoid HTTPServer's reverse-DNS lookup in server_bind()."""

    def server_bind(self) -> None:
        socketserver.TCPServer.server_bind(self)
        host, port = self.server_address[:2]
        self.server_name = host
        self.server_port = port


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    upstream = "127.0.0.1"
    upstream_port = 8787
    agent = "alice.owner"
    site_path = Path("site.json")

    def do_GET(self) -> None:
        self._route()

    def do_POST(self) -> None:
        self._route()

    def _route(self) -> None:
        parsed = urlsplit(self.path)
        path = parsed.path
        if path == "/api/health":
            self._json(200, {"ok": True, "addon": "ui-shell"})
            return
        if path == "/api/site":
            if self.command == "GET":
                return self._json(200, {"ok": True, "site": self._site()})
            if self.command == "POST":
                return self._save_site()
            return self._json(405, {"ok": False, "error": "method_not_allowed"})
        if path.startswith("/api/"):
            upstream = "/v1/" + path[len("/api/v1/"):] if path.startswith("/api/v1/") else path
            if parsed.query:
                upstream += "?" + parsed.query
            self._proxy(upstream)
            return
        self._static(path)

    def _json(self, status: int, payload: dict) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _site(self) -> dict:
        try:
            data = json.loads(self.site_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return dict(DEFAULT_SITE)
        return self._normalize_site(data)

    def _normalize_site(self, data: dict) -> dict:
        site = dict(DEFAULT_SITE)
        site["site_name"] = str(data.get("site_name") or DEFAULT_SITE["site_name"]).strip()[:80] or DEFAULT_SITE["site_name"]
        logo = str(data.get("logo_url") or "").strip()[:500]
        if logo and not (logo.startswith("https://") or logo.startswith("http://") or logo.startswith("/")):
            logo = ""
        site["logo_url"] = logo
        site["footer"] = str(data.get("footer") or "").strip()[:300]
        links = []
        for item in list(data.get("links") or [])[:8]:
            if not isinstance(item, dict):
                continue
            label = str(item.get("label") or "").strip()[:60]
            href = str(item.get("href") or "").strip()[:500]
            if label and href and (href.startswith("https://") or href.startswith("http://") or href.startswith("/") or href.startswith("mailto:")):
                links.append({"label": label, "href": href})
        site["links"] = links
        return site

    def _save_site(self) -> None:
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            return self._json(400, {"ok": False, "error": "invalid_length"})
        if length <= 0 or length > 64 * 1024:
            return self._json(400, {"ok": False, "error": "invalid_body"})
        try:
            payload = json.loads(self.rfile.read(length))
        except (ValueError, OSError):
            return self._json(400, {"ok": False, "error": "invalid_json"})
        if not isinstance(payload, dict):
            return self._json(400, {"ok": False, "error": "invalid_site"})
        site = self._normalize_site(payload)
        self.site_path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.site_path.with_suffix(".tmp")
        temp.write_text(json.dumps(site, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temp.replace(self.site_path)
        self._json(200, {"ok": True, "site": site})

    def _proxy(self, upstream_path: str) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else None
        headers = {
            key: value
            for key, value in self.headers.items()
            if key.lower() not in {"host", "origin", "x-loomsci-agent", "connection"}
        }
        headers["X-Loomsci-Agent"] = self.agent
        try:
            conn = http.client.HTTPConnection(self.upstream, self.upstream_port, timeout=20)
            conn.request(self.command, upstream_path, body=body, headers=headers)
            response = conn.getresponse()
            data = response.read()
            self.send_response(response.status)
            for key, value in response.getheaders():
                if key.lower() in {"content-length", "connection", "transfer-encoding"}:
                    continue
                self.send_header(key, value)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            conn.close()
        except Exception as exc:  # noqa: BLE001 - add-on boundary
            payload = json.dumps({"ok": False, "error": f"ui-shell proxy: {exc}"}).encode()
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    def _static(self, path: str) -> None:
        if path in ("", "/"):
            path = "/index.html"
        target = (WEB / path.lstrip("/")).resolve()
        if WEB.resolve() not in target.parents and target != WEB.resolve():
            self.send_error(404)
            return
        if not target.is_file():
            self.send_error(404)
            return
        data = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mimetypes.guess_type(str(target))[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt: str, *args) -> None:
        print("[ui-shell] " + fmt % args, flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8790)
    parser.add_argument("--home")
    parser.add_argument("--upstream", default="127.0.0.1")
    parser.add_argument("--upstream-port", type=int, default=8787)
    parser.add_argument("--agent")
    args = parser.parse_args()
    home = Path(args.home).expanduser() if args.home else None
    Handler.upstream = args.upstream
    Handler.upstream_port = args.upstream_port
    Handler.agent = args.agent or default_agent(home)
    base = home or Path.home() / ".loomsci"
    Handler.site_path = base / "packs" / "ui_shell" / "data" / "site.json"
    server = _LocalServer(("127.0.0.1", args.port), Handler)
    print(f"ui-shell on http://127.0.0.1:{args.port} (agent={Handler.agent})", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
