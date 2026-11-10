"""Minimal collab add-on: rooms and room threads over Core posts.

Room metadata lives in this add-on's SQLite store. Messages are Core posts in
the thread namespace `room:<room-id>`. Core tables and /v1 shapes are unchanged.
"""

from __future__ import annotations

import argparse
import http.client
import json
import mimetypes
import os
import secrets
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"
SCHEMA = """
CREATE TABLE IF NOT EXISTS rooms (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  topic TEXT,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS members (
  room_id TEXT NOT NULL,
  agent TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'member',
  created_at TEXT NOT NULL,
  PRIMARY KEY (room_id, agent)
);
"""


def now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def default_agent(home: Path | None = None) -> str:
    candidates = []
    if home:
        candidates.append(home)
    env_home = os.environ.get("LOOMSCI_HOME")
    if env_home:
        candidates.append(Path(env_home).expanduser())
    candidates.extend([Path.home() / ".loomsci", ROOT.parents[2]])
    for base in candidates:
        path = base / "agents" / "alice" / "agent.json"
        if path.is_file():
            try:
                return str(json.loads(path.read_text(encoding="utf-8"))["handle"])
            except (OSError, ValueError, KeyError):
                pass
    return "alice.owner"


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    upstream = "127.0.0.1"
    upstream_port = 8787
    agent = "alice.owner"
    db_path = Path("collab.db")

    def do_GET(self) -> None:
        self._route("GET")

    def do_POST(self) -> None:
        self._route("POST")

    def _route(self, method: str) -> None:
        path = urlsplit(self.path).path
        if path == "/api/health" and method == "GET":
            status, data = self._core("GET", "/v1/health")
            return self._json(status, data)
        if path == "/api/rooms" and method == "GET":
            return self._rooms()
        if path == "/api/rooms" and method == "POST":
            return self._create_room()
        if path.startswith("/api/rooms/"):
            rest = unquote(path[len("/api/rooms/"):])
            room_id, _, action = rest.partition("/")
            if not action and method == "GET":
                return self._room(room_id)
            if action == "posts" and method == "GET":
                return self._posts(room_id)
            if action == "posts" and method == "POST":
                return self._post(room_id)
        self._static(path)

    def _db(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.executescript(SCHEMA)
        conn.commit()
        return conn

    def _json(self, status: int, payload: dict) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            value = json.loads(raw.decode("utf-8"))
        except ValueError:
            return {}
        return value if isinstance(value, dict) else {}

    def _rooms(self) -> None:
        conn = self._db()
        try:
            rows = conn.execute(
                "SELECT r.*, (SELECT COUNT(*) FROM members m WHERE m.room_id=r.id) AS members "
                "FROM rooms r ORDER BY r.created_at"
            ).fetchall()
        finally:
            conn.close()
        self._json(200, {"ok": True, "rooms": [dict(row) for row in rows]})

    def _room(self, room_id: str) -> None:
        conn = self._db()
        try:
            row = conn.execute("SELECT * FROM rooms WHERE id=?", (room_id,)).fetchone()
            members = conn.execute(
                "SELECT agent, role FROM members WHERE room_id=? ORDER BY created_at",
                (room_id,),
            ).fetchall()
        finally:
            conn.close()
        if row is None:
            return self._json(404, {"ok": False, "error": "room_not_found"})
        self._json(200, {"ok": True, "room": dict(row), "members": [dict(m) for m in members]})

    def _create_room(self) -> None:
        body = self._read_json()
        name = str(body.get("name") or "").strip()
        if not name:
            return self._json(400, {"ok": False, "error": "name_required"})
        room_id = "r-" + secrets.token_hex(5)
        timestamp = now()
        conn = self._db()
        try:
            conn.execute(
                "INSERT INTO rooms(id, name, topic, created_at) VALUES (?,?,?,?)",
                (room_id, name[:80], str(body.get("topic") or "")[:200], timestamp),
            )
            conn.execute(
                "INSERT INTO members(room_id, agent, role, created_at) VALUES (?,?,?,?)",
                (room_id, self.agent, "owner", timestamp),
            )
            conn.commit()
        finally:
            conn.close()
        self._json(201, {"ok": True, "room": {"id": room_id, "name": name}})

    def _post(self, room_id: str) -> None:
        if not self._room_exists(room_id):
            return self._json(404, {"ok": False, "error": "room_not_found"})
        body = self._read_json()
        text = str(body.get("body") or "").strip()
        if not text:
            return self._json(400, {"ok": False, "error": "body_required"})
        payload = {
            "kind": "note",
            "title": str(body.get("title") or ""),
            "body": text,
            "thread_id": f"room:{room_id}",
        }
        status, data = self._core("POST", "/v1/posts", payload)
        self._json(status, data)

    def _posts(self, room_id: str) -> None:
        if not self._room_exists(room_id):
            return self._json(404, {"ok": False, "error": "room_not_found"})
        path = f"/v1/posts?thread=room:{room_id}&limit=200"
        status, data = self._core("GET", path)
        self._json(status, data)

    def _room_exists(self, room_id: str) -> bool:
        conn = self._db()
        try:
            return conn.execute("SELECT 1 FROM rooms WHERE id=?", (room_id,)).fetchone() is not None
        finally:
            conn.close()

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
        print("[collab] " + fmt % args, flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8792)
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
    Handler.db_path = base / "packs" / "collab" / "data" / "collab.db"
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"collab on http://127.0.0.1:{args.port} (agent={Handler.agent})", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
