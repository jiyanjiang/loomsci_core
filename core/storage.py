"""Minimal SQLite storage for the Core bus and task lease."""

from __future__ import annotations

import json
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

POST_KINDS = frozenset(
    {"note", "ask", "status", "review", "artifact", "handoff", "decision"}
)
TASK_STATUSES = frozenset(
    {"backlog", "claimed", "in_progress", "blocked", "done", "failed", "cancelled"}
)
SCHEMA = """
CREATE TABLE IF NOT EXISTS agents (
  handle     TEXT PRIMARY KEY,
  kind       TEXT NOT NULL DEFAULT 'ai',
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS posts (
  seq        INTEGER PRIMARY KEY AUTOINCREMENT,
  id         TEXT NOT NULL UNIQUE,
  thread_id  TEXT,
  parent_id  TEXT,
  author     TEXT NOT NULL,
  kind       TEXT NOT NULL,
  title      TEXT,
  body       TEXT NOT NULL,
  meta_json  TEXT,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS posts_seq ON posts(seq);
CREATE INDEX IF NOT EXISTS posts_thread ON posts(thread_id, seq);

CREATE TABLE IF NOT EXISTS tasks (
  id            TEXT PRIMARY KEY,
  title         TEXT NOT NULL,
  description   TEXT,
  acceptance    TEXT,
  status        TEXT NOT NULL DEFAULT 'backlog',
  assigned_to   TEXT,
  claimed_at    TEXT,
  lease_until   TEXT,
  evidence_json TEXT,
  created_at    TEXT NOT NULL,
  updated_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS tasks_status ON tasks(status, updated_at);
CREATE INDEX IF NOT EXISTS tasks_assignee ON tasks(assigned_to, status);

CREATE TABLE IF NOT EXISTS reads (
  agent      TEXT NOT NULL,
  scope      TEXT NOT NULL,
  last_seq   INTEGER NOT NULL DEFAULT 0,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (agent, scope)
);

CREATE TABLE IF NOT EXISTS presence (
  agent      TEXT NOT NULL,
  tool       TEXT NOT NULL,
  workspace  TEXT NOT NULL,
  model      TEXT,
  pid        INTEGER,
  started_at TEXT NOT NULL,
  last_seen  TEXT NOT NULL,
  PRIMARY KEY (agent, tool, workspace)
);
"""


class StorageError(RuntimeError):
    pass


class NotFound(StorageError):
    pass


class Conflict(StorageError):
    pass


class Forbidden(StorageError):
    pass


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def connect(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path)
    conn = sqlite3.connect(str(path), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 30000")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: str | Path) -> None:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=30)
    try:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def ensure_agent(conn: sqlite3.Connection, handle: str, kind: str = "ai") -> None:
    conn.execute(
        "INSERT OR IGNORE INTO agents(handle, kind, created_at) VALUES (?,?,?)",
        (handle, kind, now()),
    )


def _post_dict(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    raw = item.pop("meta_json", None)
    try:
        item["meta"] = json.loads(raw) if raw else {}
    except (TypeError, ValueError):
        item["meta"] = {}
    return item


def create_post(
    conn: sqlite3.Connection,
    *,
    author: str,
    kind: str,
    title: str = "",
    body: str,
    thread_id: str | None = None,
    parent_id: str | None = None,
    meta: dict | None = None,
) -> dict[str, Any]:
    if kind not in POST_KINDS:
        raise ValueError(f"unknown post kind: {kind}")
    if not str(body or "").strip():
        raise ValueError("body required")
    ensure_agent(conn, author)
    post_id = "p-" + secrets.token_hex(6)
    created = now()
    conn.execute(
        "INSERT INTO posts(id, thread_id, parent_id, author, kind, title, body, meta_json, created_at) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        (
            post_id,
            thread_id,
            parent_id,
            author,
            kind,
            title,
            body,
            json.dumps(meta or {}, ensure_ascii=False),
            created,
        ),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM posts WHERE id=?", (post_id,)).fetchone()
    return _post_dict(row)


def list_posts(
    conn: sqlite3.Connection,
    *,
    since: int = 0,
    limit: int = 50,
    thread_id: str | None = None,
) -> list[dict[str, Any]]:
    limit = max(1, min(int(limit), 200))
    sql = "SELECT * FROM posts WHERE seq > ?"
    params: list[Any] = [max(0, int(since))]
    if thread_id:
        sql += " AND thread_id=?"
        params.append(thread_id)
    sql += " ORDER BY seq ASC LIMIT ?"
    params.append(limit)
    return [_post_dict(row) for row in conn.execute(sql, params).fetchall()]


def _task_dict(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    raw = item.pop("evidence_json", None)
    try:
        item["evidence"] = json.loads(raw) if raw else None
    except (TypeError, ValueError):
        item["evidence"] = None
    return item


def create_task(
    conn: sqlite3.Connection,
    *,
    title: str,
    description: str = "",
    acceptance: str = "",
) -> dict[str, Any]:
    if not str(title or "").strip():
        raise ValueError("title required")
    task_id = "t-" + secrets.token_hex(6)
    timestamp = now()
    conn.execute(
        "INSERT INTO tasks(id, title, description, acceptance, status, created_at, updated_at) "
        "VALUES (?,?,?,?, 'backlog', ?, ?)",
        (task_id, title, description, acceptance, timestamp, timestamp),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
    return _task_dict(row)


def list_tasks(
    conn: sqlite3.Connection,
    *,
    status: str | None = None,
    assigned_to: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    limit = max(1, min(int(limit), 200))
    sql = "SELECT * FROM tasks WHERE 1=1"
    params: list[Any] = []
    if status:
        sql += " AND status=?"
        params.append(status)
    if assigned_to:
        sql += " AND assigned_to=?"
        params.append(assigned_to)
    sql += " ORDER BY updated_at DESC LIMIT ?"
    params.append(limit)
    return [_task_dict(row) for row in conn.execute(sql, params).fetchall()]


def claim_task(
    conn: sqlite3.Connection,
    *,
    task_id: str,
    agent: str,
    lease_seconds: int = 3600,
) -> dict[str, Any]:
    timestamp = now()
    lease_until = (
        datetime.now(timezone.utc) + timedelta(seconds=max(60, int(lease_seconds)))
    ).replace(microsecond=0).isoformat()
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        if row is None:
            raise NotFound("task not found")
        if row["status"] in {"done", "cancelled", "failed"}:
            raise Conflict(f"task is {row['status']}")
        current = row["assigned_to"]
        current_lease = row["lease_until"]
        if current and current != agent and current_lease and current_lease > timestamp:
            raise Conflict(f"task is leased by {current}")
        conn.execute(
            "UPDATE tasks SET assigned_to=?, status='claimed', claimed_at=COALESCE(claimed_at, ?), "
            "lease_until=?, updated_at=? WHERE id=?",
            (agent, timestamp, lease_until, timestamp, task_id),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
    return _task_dict(row)


def done_task(
    conn: sqlite3.Connection,
    *,
    task_id: str,
    agent: str,
    evidence: dict | str,
) -> dict[str, Any]:
    row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
    if row is None:
        raise NotFound("task not found")
    if row["assigned_to"] != agent:
        raise Forbidden("only the assignee can complete this task")
    payload = evidence if isinstance(evidence, dict) else {"note": evidence}
    if not payload:
        raise ValueError("evidence required")
    conn.execute(
        "UPDATE tasks SET status='done', evidence_json=?, lease_until=NULL, updated_at=? WHERE id=?",
        (json.dumps(payload, ensure_ascii=False), now(), task_id),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
    return _task_dict(row)


def upsert_presence(
    conn: sqlite3.Connection,
    *,
    agent: str,
    tool: str,
    workspace: str,
    model: str = "",
    pid: int | None = None,
) -> None:
    timestamp = now()
    ensure_agent(conn, agent)
    conn.execute(
        "INSERT INTO presence(agent, tool, workspace, model, pid, started_at, last_seen) "
        "VALUES (?,?,?,?,?,?,?) "
        "ON CONFLICT(agent, tool, workspace) DO UPDATE SET "
        "model=excluded.model, pid=excluded.pid, last_seen=excluded.last_seen",
        (agent, tool, workspace, model, pid, timestamp, timestamp),
    )
    conn.commit()


def set_read_cursor(
    conn: sqlite3.Connection, *, agent: str, scope: str, last_seq: int
) -> None:
    ensure_agent(conn, agent)
    conn.execute(
        "INSERT INTO reads(agent, scope, last_seq, updated_at) VALUES (?,?,?,?) "
        "ON CONFLICT(agent, scope) DO UPDATE SET last_seq=excluded.last_seq, updated_at=excluded.updated_at",
        (agent, scope, max(0, int(last_seq)), now()),
    )
    conn.commit()


def get_read_cursor(conn: sqlite3.Connection, *, agent: str, scope: str) -> int:
    row = conn.execute(
        "SELECT last_seq FROM reads WHERE agent=? AND scope=?", (agent, scope)
    ).fetchone()
    return int(row["last_seq"]) if row else 0
