"""Minimal notify add-on: unread digest over Core inbox/tasks/posts.

No local database. It reads Core /v1 and can mark inbox items read. Desktop
notifications are best-effort and optional (macOS osascript, Windows msg.exe).
"""

from __future__ import annotations

import argparse
import socketserver
import http.client
import json
import mimetypes
import os
import subprocess
import sys
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"
OPEN_TASK_STATES = {"backlog", "claimed", "in_progress", "blocked"}


def default_agent(home: Path | None = None) -> str:
    base = home or Path(os.environ.get("LOOMSCI_HOME", str(Path.home() / ".loomsci")))
    path = base / "agents" / "alice" / "agent.json"
    if path.is_file():
        try:
            return str(json.loads(path.read_text(encoding="utf-8"))["handle"])
        except (OSError, ValueError, KeyError):
            pass
    return "alice.owner"


def desktop_notify(title: str, message: str) -> bool:
    try:
        if sys.platform == "darwin":
            script = f'display notification {json.dumps(message)} with title {json.dumps(title)}'
            subprocess.run(["osascript", "-e", script], check=True, timeout=10,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        if os.name == "nt":
            subprocess.run(["msg", "*", f"{title}: {message}"], check=True, timeout=10,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
    except (OSError, subprocess.SubprocessError):
        return False
    return False


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

    def do_GET(self) -> None:
        self._route("GET")

    def do_POST(self) -> None:
        self._route("POST")

    def _route(self, method: str) -> None:
        path = urlsplit(self.path).path
        if path == "/api/health" and method == "GET":
            return self._json(200, {"ok": True, "addon": "notify"})
        if path == "/api/summary" and method == "GET":
            return self._summary()
        if path == "/api/digest" and method == "GET":
            return self._digest()
        if path == "/api/read-all" and method == "POST":
            return self._read_all()
        self._static(path)

    def _json(self, status: int, payload: dict) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _core(self, method: str, path: str, payload: dict | None = None) -> tuple[int, dict]:
        data = json.dumps(payload).encode() if payload is not None else None
        headers = {"X-Loomsci-Agent": self.agent}
        if data:
            headers["Content-Type"] = "application/json"
        try:
            conn = http.client.HTTPConnection(self.upstream, self.upstream_port, timeout=20)
            conn.request(method, path, body=data, headers=headers)
            response = conn.getresponse()
            raw = response.read()
            conn.close()
            return response.status, json.loads(raw or b"{}")
        except Exception as exc:  # noqa: BLE001 - add-on boundary
            return 502, {"ok": False, "error": f"core proxy: {exc}"}

    def _summary(self) -> None:
        inbox_status, inbox = self._core("GET", "/v1/inbox?unread=1&limit=200")
        task_status, tasks = self._core("GET", "/v1/tasks?limit=200")
        post_status, posts = self._core("GET", "/v1/posts?since=0&limit=200")
        if 200 not in (inbox_status, task_status, post_status):
            return self._json(502, {
                "ok": False,
                "error": "core_unreachable",
                "status": [inbox_status, task_status, post_status],
            })
        open_tasks = [t for t in tasks.get("tasks", []) if t.get("status") in OPEN_TASK_STATES]
        self._json(200, {
            "ok": True,
            "agent": self.agent,
            "unread": len(inbox.get("inbox", [])),
            "open_tasks": len(open_tasks),
            "posts": len(posts.get("posts", [])),
            "inbox": inbox.get("inbox", [])[:20],
            "tasks": open_tasks[:20],
        })

    def _digest(self) -> None:
        status, data = self._core("GET", "/v1/inbox?unread=1&limit=200")
        task_status, tasks = self._core("GET", "/v1/tasks?limit=200")
        if status != 200 or task_status != 200:
            return self._json(502, {"ok": False, "error": "core_unreachable"})
        unread = data.get("inbox", [])
        open_tasks = [t for t in tasks.get("tasks", []) if t.get("status") in OPEN_TASK_STATES]
        lines = [
            "# Notify digest",
            "",
            f"- unread mentions: **{len(unread)}**",
            f"- open tasks: **{len(open_tasks)}**",
            "",
            "## Unread",
        ]
        unread_lines = [
            f"- #{item.get('seq')} **{item.get('title') or item.get('id')}** · {item.get('author')}"
            for item in unread[:10]
        ]
        lines.extend(unread_lines or ["- (none)"])
        lines.append("")
        lines.append("## Open tasks")
        task_lines = [
            f"- **{item.get('title') or item.get('id')}** · {item.get('status')} · {item.get('assigned_to') or 'unassigned'}"
            for item in open_tasks[:10]
        ]
        lines.extend(task_lines or ["- (none)"])
        self._json(200, {"ok": True, "markdown": "\n".join(lines), "unread": len(unread), "open_tasks": len(open_tasks)})

    def _read_all(self) -> None:
        status, data = self._core("POST", "/v1/inbox/read", {})
        self._json(status, data)

    def _static(self, path: str) -> None:
        if path in ("", "/"):
            path = "/index.html"
        target = (WEB / path.lstrip("/")).resolve()
        if WEB.resolve() not in target.parents and target != WEB.resolve():
            return self.send_error(404)
        if not target.is_file():
            return self.send_error(404)
        data = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mimetypes.guess_type(str(target))[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt: str, *args) -> None:
        print("[notify] " + fmt % args, flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8793)
    parser.add_argument("--home")
    parser.add_argument("--upstream", default="127.0.0.1")
    parser.add_argument("--upstream-port", type=int, default=8787)
    parser.add_argument("--agent")
    parser.add_argument("--desktop", action="store_true")
    args = parser.parse_args()
    home = Path(args.home).expanduser() if args.home else None
    Handler.upstream = args.upstream
    Handler.upstream_port = args.upstream_port
    Handler.agent = args.agent or default_agent(home)
    if args.desktop:
        # One-shot diagnostic; a polling loop belongs to the user's launcher.
        print("desktop_notify available:", desktop_notify("loomsci notify", "desktop notifications enabled"), flush=True)
    server = _LocalServer(("127.0.0.1", args.port), Handler)
    print(f"notify on http://127.0.0.1:{args.port} (agent={Handler.agent})", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
