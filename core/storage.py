"""Minimal SQLite storage for the Core bus and task lease."""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

MENTION_RE = re.compile(r"@([a-z0-9][a-z0-9-]{0,31}\.[a-z0-9][a-z0-9-]{0,31})")
ATTACHMENT_MAX_BYTES = 512 * 1024

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

CREATE TABLE IF NOT EXISTS agent_aliases (
  alias      TEXT PRIMARY KEY,
  handle     TEXT NOT NULL,
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

CREATE TABLE IF NOT EXISTS mentions (
  post_seq   INTEGER NOT NULL,
  agent      TEXT NOT NULL,
  created_at TEXT NOT NULL,
  read_at    TEXT,
  PRIMARY KEY (post_seq, agent)
);
CREATE INDEX IF NOT EXISTS mentions_agent ON mentions(agent, read_at);

CREATE TABLE IF NOT EXISTS attachments (
  id           TEXT PRIMARY KEY,
  post_id      TEXT,
  filename     TEXT NOT NULL,
  content_type TEXT,
  bytes        INTEGER NOT NULL,
  sha256       TEXT NOT NULL,
  created_at   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS attachments_post ON attachments(post_id);

CREATE TABLE IF NOT EXISTS facts (
  id          TEXT PRIMARY KEY,
  project     TEXT,
  claim       TEXT NOT NULL,
  evidence    TEXT,
  source      TEXT,
  tags        TEXT,
  status      TEXT NOT NULL DEFAULT 'candidate',
  confidence  REAL,
  created_by  TEXT,
  reviewed_by TEXT,
  created_at  TEXT NOT NULL,
  updated_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS facts_status ON facts(status, updated_at);
CREATE INDEX IF NOT EXISTS facts_project ON facts(project, status);

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


def _chmod_private(path: Path) -> None:
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def connect(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path)
    conn = sqlite3.connect(str(path), timeout=30)
    _chmod_private(path)
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
    _chmod_private(path)
    for suffix in ("-wal", "-shm"):
        _chmod_private(Path(str(path) + suffix))


def ensure_agent(conn: sqlite3.Connection, handle: str, kind: str = "ai") -> None:
    conn.execute(
        "INSERT OR IGNORE INTO agents(handle, kind, created_at) VALUES (?,?,?)",
        (handle, kind, now()),
    )


def record_alias(conn: sqlite3.Connection, alias: str, handle: str) -> None:
    conn.execute(
        "INSERT INTO agent_aliases(alias, handle, created_at) VALUES (?,?,?) "
        "ON CONFLICT(alias) DO UPDATE SET handle=excluded.handle",
        (alias, handle, now()),
    )
    conn.commit()


def list_agents(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in conn.execute(
            "SELECT handle, kind, created_at FROM agents ORDER BY handle"
        ).fetchall()
    ]


def delete_agent(conn: sqlite3.Connection, handle: str) -> bool:
    conn.execute("DELETE FROM agent_aliases WHERE handle=? OR alias=?", (handle, handle))
    cursor = conn.execute("DELETE FROM agents WHERE handle=?", (handle,))
    conn.commit()
    return cursor.rowcount > 0


def agent_exists(conn: sqlite3.Connection, handle: str) -> bool:
    row = conn.execute("SELECT 1 FROM agents WHERE handle=?", (handle,)).fetchone()
    return row is not None


def resolve_handle(conn: sqlite3.Connection, handle: str) -> str:
    row = conn.execute(
        "SELECT handle FROM agent_aliases WHERE alias=?", (handle,)
    ).fetchone()
    return str(row["handle"]) if row else handle


def _extract_mentions(text: str) -> list[str]:
    return [match.group(1).lower() for match in MENTION_RE.finditer(text or "")]


def list_mentions(conn: sqlite3.Connection, *, post_id: str) -> list[str]:
    rows = conn.execute(
        "SELECT m.agent FROM mentions m JOIN posts p ON p.seq=m.post_seq WHERE p.id=? ORDER BY m.agent",
        (post_id,),
    ).fetchall()
    return [row[0] for row in rows]


def list_inbox(
    conn: sqlite3.Connection,
    *,
    agent: str,
    unread_only: bool = False,
    limit: int = 50,
) -> list[dict[str, Any]]:
    limit = max(1, min(int(limit), 200))
    sql = (
        "SELECT p.*, m.read_at AS mention_read_at FROM mentions m "
        "JOIN posts p ON p.seq=m.post_seq WHERE m.agent=?"
    )
    params: list[Any] = [agent]
    if unread_only:
        sql += " AND m.read_at IS NULL"
    sql += " ORDER BY p.seq DESC LIMIT ?"
    params.append(limit)
    items = []
    for row in conn.execute(sql, params).fetchall():
        item = _post_dict(row)
        item["mention_read_at"] = item.pop("mention_read_at", None)
        items.append(item)
    return items


def mark_inbox_read(
    conn: sqlite3.Connection,
    *,
    agent: str,
    post_id: str | None = None,
    up_to_seq: int | None = None,
) -> int:
    if post_id:
        row = conn.execute("SELECT seq FROM posts WHERE id=?", (post_id,)).fetchone()
        if row is None:
            raise NotFound("post not found")
        cursor = conn.execute(
            "UPDATE mentions SET read_at=? WHERE agent=? AND post_seq=? AND read_at IS NULL",
            (now(), agent, int(row[0])),
        )
    elif up_to_seq is not None:
        cursor = conn.execute(
            "UPDATE mentions SET read_at=? WHERE agent=? AND post_seq<=? AND read_at IS NULL",
            (now(), agent, int(up_to_seq)),
        )
    else:
        cursor = conn.execute(
            "UPDATE mentions SET read_at=? WHERE agent=? AND read_at IS NULL",
            (now(), agent),
        )
    conn.commit()
    return cursor.rowcount


def add_attachment(
    conn: sqlite3.Connection,
    *,
    filename: str,
    content_type: str,
    data: bytes,
    blob_dir: Path,
) -> dict[str, Any]:
    if not data:
        raise ValueError("empty attachment")
    if len(data) > ATTACHMENT_MAX_BYTES:
        raise ValueError("attachment too large")
    safe_name = re.sub(r"[^A-Za-z0-9._ -]+", "_", Path(str(filename or "file")).name).strip() or "file"
    safe_name = safe_name[:120]
    attachment_id = "a-" + secrets.token_hex(6)
    digest = hashlib.sha256(data).hexdigest()
    blob_dir.mkdir(parents=True, exist_ok=True)
    target = blob_dir / attachment_id
    target.write_bytes(data)
    try:
        target.chmod(0o600)
    except OSError:
        pass
    created = now()
    conn.execute(
        "INSERT INTO attachments(id, filename, content_type, bytes, sha256, created_at) "
        "VALUES (?,?,?,?,?,?)",
        (attachment_id, safe_name, content_type or "application/octet-stream",
         len(data), digest, created),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM attachments WHERE id=?", (attachment_id,)).fetchone()
    return dict(row)


def get_attachment(conn: sqlite3.Connection, attachment_id: str) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM attachments WHERE id=?", (attachment_id,)).fetchone()
    return dict(row) if row else None


def attach_to_post(
    conn: sqlite3.Connection, *, attachment_id: str, post_id: str
) -> dict[str, Any]:
    row = get_attachment(conn, attachment_id)
    if row is None:
        raise NotFound("attachment not found")
    if row.get("post_id") and row["post_id"] != post_id:
        raise Conflict("attachment already linked")
    conn.execute("UPDATE attachments SET post_id=? WHERE id=?", (post_id, attachment_id))
    conn.commit()
    return get_attachment(conn, attachment_id) or row


def list_attachments(conn: sqlite3.Connection, *, post_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT id, filename, content_type, bytes, sha256, created_at "
        "FROM attachments WHERE post_id=? ORDER BY created_at",
        (post_id,),
    ).fetchall()
    return [dict(row) for row in rows]


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
    attachments: list[str] | None = None,
) -> dict[str, Any]:
    if kind not in POST_KINDS:
        raise ValueError(f"unknown post kind: {kind}")
    if not str(body or "").strip():
        raise ValueError("body required")
    ensure_agent(conn, author)
    attachment_ids = list(attachments or [])
    for attachment_id in attachment_ids:
        attached = get_attachment(conn, attachment_id)
        if attached is None:
            raise NotFound("attachment not found")
        if attached.get("post_id"):
            raise Conflict("attachment already linked")
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
    seq = int(conn.execute("SELECT seq FROM posts WHERE id=?", (post_id,)).fetchone()[0])
    for agent in sorted(set(_extract_mentions(f"{title} {body}"))):
        conn.execute(
            "INSERT OR IGNORE INTO mentions(post_seq, agent, created_at) VALUES (?,?,?)",
            (seq, agent, created),
        )
    for attachment_id in attachment_ids:
        attach_to_post(conn, attachment_id=attachment_id, post_id=post_id)
    conn.commit()
    row = conn.execute("SELECT * FROM posts WHERE id=?", (post_id,)).fetchone()
    item = _post_dict(row)
    item["mentions"] = list_mentions(conn, post_id=post_id)
    item["attachments"] = list_attachments(conn, post_id=post_id)
    return item


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
    items = []
    for row in conn.execute(sql, params).fetchall():
        item = _post_dict(row)
        item["mentions"] = list_mentions(conn, post_id=item["id"])
        item["attachments"] = list_attachments(conn, post_id=item["id"])
        items.append(item)
    return items


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


def get_task(conn: sqlite3.Connection, task_id: str) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
    return _task_dict(row) if row else None


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


def add_fact(
    conn: sqlite3.Connection,
    *,
    claim: str,
    evidence: str = "",
    source: str = "",
    project: str = "",
    tags: str = "",
    created_by: str = "",
    confidence: float | None = None,
) -> dict[str, Any]:
    text = str(claim or "").strip()
    if not text:
        raise ValueError("claim required")
    fact_id = "f-" + secrets.token_hex(6)
    timestamp = now()
    conn.execute(
        "INSERT INTO facts(id, project, claim, evidence, source, tags, status, confidence, "
        "created_by, created_at, updated_at) VALUES (?,?,?,?,?,?, 'candidate', ?,?,?,?)",
        (fact_id, project, text, evidence, source, tags, confidence, created_by,
         timestamp, timestamp),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM facts WHERE id=?", (fact_id,)).fetchone()
    return dict(row)


def list_facts(
    conn: sqlite3.Connection,
    *,
    q: str = "",
    status: str | None = None,
    project: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    limit = max(1, min(int(limit), 200))
    sql = "SELECT * FROM facts WHERE 1=1"
    params: list[Any] = []
    if status:
        sql += " AND status=?"
        params.append(status)
    if project:
        sql += " AND project=?"
        params.append(project)
    if q:
        sql += " AND (claim LIKE ? OR evidence LIKE ? OR source LIKE ?)"
        like = f"%{q}%"
        params.extend([like, like, like])
    sql += " ORDER BY updated_at DESC LIMIT ?"
    params.append(limit)
    return [dict(row) for row in conn.execute(sql, params).fetchall()]


def get_fact(conn: sqlite3.Connection, fact_id: str) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM facts WHERE id=?", (fact_id,)).fetchone()
    return dict(row) if row else None


def review_fact(
    conn: sqlite3.Connection,
    *,
    fact_id: str,
    status: str,
    reviewer: str,
) -> dict[str, Any]:
    allowed = {"candidate", "approved", "rejected", "archived"}
    if status not in allowed:
        raise ValueError(f"status must be one of {sorted(allowed)}")
    row = get_fact(conn, fact_id)
    if row is None:
        raise NotFound("fact not found")
    conn.execute(
        "UPDATE facts SET status=?, reviewed_by=?, updated_at=? WHERE id=?",
        (status, reviewer, now(), fact_id),
    )
    conn.commit()
    return get_fact(conn, fact_id) or row


def list_presence(
    conn: sqlite3.Connection, *, agent: str | None = None
) -> list[dict[str, Any]]:
    if agent:
        rows = conn.execute(
            "SELECT * FROM presence WHERE agent=? ORDER BY last_seen DESC", (agent,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM presence ORDER BY last_seen DESC"
        ).fetchall()
    return [dict(row) for row in rows]


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


def search(
    conn: sqlite3.Connection, *, q: str, limit: int = 50
) -> list[dict[str, Any]]:
    text = str(q or "").strip()
    if not text:
        return []
    limit = max(1, min(int(limit), 100))
    like = f"%{text}%"
    results: list[dict[str, Any]] = []
    for row in conn.execute(
        "SELECT * FROM posts WHERE title LIKE ? OR body LIKE ? ORDER BY seq DESC LIMIT ?",
        (like, like, limit),
    ).fetchall():
        post = _post_dict(row)
        results.append({
            "type": "post",
            "id": post["id"],
            "title": post.get("title") or post["id"],
            "snippet": str(post.get("body") or "")[:240],
            "created_at": post.get("created_at"),
        })
    for row in conn.execute(
        "SELECT * FROM tasks WHERE title LIKE ? OR description LIKE ? OR acceptance LIKE ? "
        "ORDER BY updated_at DESC LIMIT ?",
        (like, like, like, limit),
    ).fetchall():
        task = _task_dict(row)
        results.append({
            "type": "task",
            "id": task["id"],
            "title": task.get("title") or task["id"],
            "snippet": str(task.get("acceptance") or task.get("description") or "")[:240],
            "created_at": task.get("updated_at"),
        })
    for row in conn.execute(
        "SELECT * FROM facts WHERE claim LIKE ? OR evidence LIKE ? OR source LIKE ? "
        "ORDER BY updated_at DESC LIMIT ?",
        (like, like, like, limit),
    ).fetchall():
        fact = dict(row)
        results.append({
            "type": "fact",
            "id": fact["id"],
            "title": fact.get("claim") or fact["id"],
            "snippet": str(fact.get("evidence") or fact.get("source") or "")[:240],
            "created_at": fact.get("updated_at"),
        })
    results.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
    return results[:limit]


def stats(conn: sqlite3.Connection) -> dict[str, Any]:
    counts = {
        table: int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
        for table in (
            "agents", "posts", "tasks", "facts", "mentions", "attachments",
        )
    }
    last_seq = int(conn.execute("SELECT COALESCE(MAX(seq), 0) FROM posts").fetchone()[0])
    try:
        integrity = str(conn.execute("PRAGMA quick_check").fetchone()[0])
    except sqlite3.DatabaseError as exc:
        integrity = f"error: {exc}"
    return {"counts": counts, "last_seq": last_seq, "integrity": integrity}
