"""Minimal Core v0 storage prototype.

Not product code. Defines the M1 schema and storage behavior:
items, item_tags, blobs, apps, FTS.
"""

from __future__ import annotations

import hashlib
import json
import re
import secrets
import shutil
import sqlite3
import time
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 2

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
  id TEXT PRIMARY KEY,
  app TEXT NOT NULL,
  type TEXT NOT NULL,
  title TEXT,
  body TEXT,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  deleted_at TEXT
);
CREATE INDEX IF NOT EXISTS items_app_type ON items(app, type);
CREATE INDEX IF NOT EXISTS items_updated ON items(updated_at);
CREATE INDEX IF NOT EXISTS items_deleted ON items(deleted_at);

CREATE TABLE IF NOT EXISTS item_tags (
  item_id TEXT NOT NULL,
  tag TEXT NOT NULL,
  source TEXT NOT NULL DEFAULT 'ai',
  confidence REAL,
  PRIMARY KEY (item_id, tag)
);
CREATE INDEX IF NOT EXISTS item_tags_tag ON item_tags(tag, item_id);

CREATE TABLE IF NOT EXISTS blobs (
  id TEXT PRIMARY KEY,
  item_id TEXT,
  filename TEXT NOT NULL,
  content_type TEXT,
  bytes INTEGER NOT NULL,
  sha256 TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS blobs_item ON blobs(item_id);

CREATE TABLE IF NOT EXISTS apps (
  slug TEXT PRIMARY KEY,
  version TEXT NOT NULL,
  manifest_json TEXT NOT NULL,
  installed_at TEXT NOT NULL
);

CREATE VIRTUAL TABLE IF NOT EXISTS items_fts USING fts5(
  id UNINDEXED, title, body, tags, app, tokenize='unicode61'
);
"""


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def init_db(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        conn.execute("PRAGMA journal_mode = WAL")
        version = int(conn.execute("PRAGMA user_version").fetchone()[0])
        if version > SCHEMA_VERSION:
            raise RuntimeError(
                f"database schema {version} is newer than supported {SCHEMA_VERSION}"
            )
        if version < SCHEMA_VERSION and path.stat().st_size > 0:
            stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
            shutil.copy2(path, path.with_name(path.name + f".pre-v{SCHEMA_VERSION}-{stamp}"))
        conn.executescript(SCHEMA)
        cols = {row[1] for row in conn.execute("PRAGMA table_info(items)").fetchall()}
        if "deleted_at" not in cols:
            conn.execute("ALTER TABLE items ADD COLUMN deleted_at TEXT")
        conn.execute("CREATE INDEX IF NOT EXISTS items_deleted ON items(deleted_at)")
        conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        conn.commit()
    finally:
        conn.close()


def connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 30000")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _id(prefix: str) -> str:
    return prefix + secrets.token_hex(6)


def _slug(value: str, what: str) -> str:
    token = str(value or "").strip()
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", token):
        raise ValueError(f"invalid {what}")
    return token


def _tag(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lstrip("#")).casefold()[:40]


def _refresh_fts(conn: sqlite3.Connection, item_id: str) -> None:
    conn.execute("DELETE FROM items_fts WHERE id=?", (item_id,))
    row = conn.execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone()
    if row is None or row["deleted_at"]:
        return
    tags = conn.execute(
        "SELECT group_concat(tag, ' ') FROM item_tags WHERE item_id=?", (item_id,)
    ).fetchone()[0] or ""
    conn.execute(
        "INSERT INTO items_fts(id,title,body,tags,app) VALUES (?,?,?,?,?)",
        (row["id"], row["title"] or "", row["body"] or "", tags, row["app"]),
    )


def _item(row: sqlite3.Row, tags: list[dict]) -> dict[str, Any]:
    item = dict(row)
    try:
        item["metadata"] = json.loads(item.pop("metadata_json") or "{}")
    except ValueError:
        item["metadata"] = {}
    item["tags"] = tags
    return item


def _tags(conn: sqlite3.Connection, item_id: str) -> list[dict]:
    return [dict(row) for row in conn.execute(
        "SELECT tag, source, confidence FROM item_tags WHERE item_id=? ORDER BY tag", (item_id,)
    ).fetchall()]


def _hash_name(sha256: str, filename: str) -> str:
    suffix = Path(filename or "").suffix.lower()
    return (sha256 or "")[:16] + suffix


def _blobs(conn: sqlite3.Connection, item_id: str) -> list[dict]:
    rows = [dict(row) for row in conn.execute(
        "SELECT id, filename, content_type, bytes, sha256, created_at FROM blobs WHERE item_id=? ORDER BY created_at",
        (item_id,),
    ).fetchall()]
    for row in rows:
        row["hash_name"] = _hash_name(str(row.get("sha256") or ""), str(row.get("filename") or ""))
    return rows


def create_item(
    conn: sqlite3.Connection,
    *,
    app: str,
    type: str,
    title: str = "",
    body: str = "",
    metadata: dict | None = None,
    tags: list[str] | None = None,
    item_id: str | None = None,
) -> dict[str, Any]:
    app = _slug(app, "app")
    kind = _slug(type.replace(".", "-"), "type").replace("-", ".")
    stamp = now()
    item_id = item_id or _id("i-")
    conn.execute(
        "INSERT INTO items(id,app,type,title,body,metadata_json,created_at,updated_at) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (item_id, app, kind, title, body, json.dumps(metadata or {}, ensure_ascii=False), stamp, stamp),
    )
    if tags:
        set_tags(conn, item_id=item_id, tags=tags)
    _refresh_fts(conn, item_id)
    conn.commit()
    return get_item(conn, item_id)  # type: ignore[return-value]


def set_tags(
    conn: sqlite3.Connection, *, item_id: str, tags: list[str], source: str = "ai"
) -> list[dict]:
    conn.execute("DELETE FROM item_tags WHERE item_id=?", (item_id,))
    seen: list[str] = []
    for value in list(tags or [])[:8]:
        tag = _tag(value)
        if tag and tag not in seen:
            seen.append(tag)
    for tag in seen:
        conn.execute(
            "INSERT INTO item_tags(item_id,tag,source,confidence) VALUES (?,?,?,NULL)",
            (item_id, tag, source),
        )
    _refresh_fts(conn, item_id)
    conn.commit()
    return _tags(conn, item_id)


def get_item(conn: sqlite3.Connection, item_id: str, *, include_deleted: bool = False) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone()
    if row is None:
        return None
    if row["deleted_at"] and not include_deleted:
        return None
    item = _item(row, _tags(conn, item_id))
    item["blobs"] = _blobs(conn, item_id)
    return item


def list_items(
    conn: sqlite3.Connection,
    *,
    app: str = "",
    type: str = "",
    tag: str = "",
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    sql = "SELECT * FROM items WHERE deleted_at IS NULL"
    params: list[Any] = []
    if app:
        sql += " AND app=?"
        params.append(app)
    if type:
        sql += " AND type=?"
        params.append(type)
    if tag:
        sql += " AND id IN (SELECT item_id FROM item_tags WHERE tag=?)"
        params.append(_tag(tag))
    sql += " ORDER BY updated_at DESC, id LIMIT ? OFFSET ?"
    params += [max(1, min(int(limit), 200)), max(0, int(offset))]
    rows = conn.execute(sql, params).fetchall()
    ids = [row["id"] for row in rows]
    by_id: dict[str, list[dict]] = {}
    if ids:
        placeholders = ",".join("?" for _ in ids)
        for tag_row in conn.execute(
            f"SELECT item_id,tag,source,confidence FROM item_tags WHERE item_id IN ({placeholders}) ORDER BY tag",
            ids,
        ):
            by_id.setdefault(tag_row["item_id"], []).append(dict(tag_row))
    out = []
    for row in rows:
        item = _item(row, by_id.get(row["id"], []))
        item["blobs"] = _blobs(conn, row["id"])
        out.append(item)
    return out


def update_item(conn: sqlite3.Connection, item_id: str, **fields: Any) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone()
    if row is None or row["deleted_at"]:
        return None
    allowed = {"title", "body", "metadata"}
    updates = []
    params: list[Any] = []
    for key in allowed:
        if key in fields:
            value = fields[key]
            if key == "metadata":
                value = json.dumps(value or {}, ensure_ascii=False)
                key = "metadata_json"
            updates.append(f"{key}=?")
            params.append(value)
    if updates:
        updates.append("updated_at=?")
        params.extend([now(), item_id])
        conn.execute(f"UPDATE items SET {', '.join(updates)} WHERE id=?", params)
        _refresh_fts(conn, item_id)
        conn.commit()
    return get_item(conn, item_id)


def delete_item(conn: sqlite3.Connection, item_id: str, *,
                hard: bool = False, blob_dir: Path | None = None) -> bool:
    """Soft-delete by default; hard delete removes item, tags, FTS and blobs."""
    row = conn.execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone()
    if row is None:
        return False
    if not hard:
        conn.execute("UPDATE items SET deleted_at=?, updated_at=? WHERE id=?",
                     (now(), now(), item_id))
        conn.execute("DELETE FROM items_fts WHERE id=?", (item_id,))
        conn.commit()
        return True
    blobs = conn.execute("SELECT id FROM blobs WHERE item_id=?", (item_id,)).fetchall()
    if blob_dir is not None:
        for blob in blobs:
            try:
                (blob_dir / blob["id"]).unlink(missing_ok=True)
            except OSError:
                pass
    conn.execute("DELETE FROM blobs WHERE item_id=?", (item_id,))
    conn.execute("DELETE FROM item_tags WHERE item_id=?", (item_id,))
    conn.execute("DELETE FROM items_fts WHERE id=?", (item_id,))
    changed = conn.execute("DELETE FROM items WHERE id=?", (item_id,)).rowcount
    conn.commit()
    return bool(changed)


def restore_item(conn: sqlite3.Connection, item_id: str) -> bool:
    row = conn.execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone()
    if row is None or not row["deleted_at"]:
        return False
    conn.execute("UPDATE items SET deleted_at=NULL, updated_at=? WHERE id=?", (now(), item_id))
    _refresh_fts(conn, item_id)
    conn.commit()
    return True


def list_deleted(conn: sqlite3.Connection, *, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM items WHERE deleted_at IS NOT NULL ORDER BY deleted_at DESC LIMIT ? OFFSET ?",
        (max(1, min(int(limit), 200)), max(0, int(offset))),
    ).fetchall()
    return [_item(row, _tags(conn, row["id"])) | {"blobs": _blobs(conn, row["id"])} for row in rows]


def purge_deleted(conn: sqlite3.Connection, *, blob_dir: Path | None = None) -> int:
    ids = [row["id"] for row in conn.execute(
        "SELECT id FROM items WHERE deleted_at IS NOT NULL").fetchall()]
    for item_id in ids:
        delete_item(conn, item_id, hard=True, blob_dir=blob_dir)
    return len(ids)


def list_tags(conn: sqlite3.Connection, *, limit: int = 100, app: str = "") -> list[dict[str, Any]]:
    sql = ("SELECT item_tags.tag, COUNT(*) AS count FROM item_tags "
           "JOIN items ON items.id=item_tags.item_id "
           "WHERE items.deleted_at IS NULL")
    params: list[Any] = []
    if app:
        sql += " AND items.app=?"
        params.append(app)
    sql += " GROUP BY item_tags.tag ORDER BY count DESC, item_tags.tag LIMIT ?"
    params.append(max(1, min(int(limit), 1000)))
    return [dict(row) for row in conn.execute(sql, params).fetchall()]


def search(conn: sqlite3.Connection, q: str, *, limit: int = 50, app: str = "") -> list[dict[str, Any]]:
    terms = [term for term in re.split(r"\s+", str(q or "").strip()) if term]
    if not terms:
        return []
    query = " AND ".join('"' + term.replace('"', '""') + '"' for term in terms)
    sql = "SELECT id FROM items_fts WHERE items_fts MATCH ?"
    params: list[Any] = [query]
    if app:
        sql += " AND app=?"
        params.append(app)
    sql += " ORDER BY rank LIMIT ?"
    params.append(max(1, min(int(limit), 100)))
    rows = conn.execute(sql, params).fetchall()
    return [item for row in rows if (item := get_item(conn, row["id"])) is not None]


def add_blob(
    conn: sqlite3.Connection,
    *,
    blob_dir: Path,
    filename: str,
    content_type: str,
    data: bytes,
    item_id: str | None = None,
) -> dict[str, Any]:
    if not data:
        raise ValueError("empty blob")
    if item_id and conn.execute("SELECT 1 FROM items WHERE id=?", (item_id,)).fetchone() is None:
        raise ValueError("item not found")
    digest = hashlib.sha256(data).hexdigest()
    if item_id:
        existing = conn.execute(
            "SELECT * FROM blobs WHERE item_id=? AND sha256=? ORDER BY created_at LIMIT 1",
            (item_id, digest),
        ).fetchone()
        if existing is not None:
            result = dict(existing)
            result["hash_name"] = _hash_name(digest, str(result.get("filename") or ""))
            return result
    blob_id = _id("b-")
    blob_dir.mkdir(parents=True, exist_ok=True)
    (blob_dir / blob_id).write_bytes(data)
    stamp = now()
    conn.execute(
        "INSERT INTO blobs(id,item_id,filename,content_type,bytes,sha256,created_at) "
        "VALUES (?,?,?,?,?,?,?)",
        (blob_id, item_id, Path(filename).name or "file", content_type, len(data), digest, stamp),
    )
    conn.commit()
    return get_blob(conn, blob_id)  # type: ignore[return-value]


def get_blob(conn: sqlite3.Connection, blob_id: str) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM blobs WHERE id=?", (blob_id,)).fetchone()
    if row is None:
        return None
    result = dict(row)
    result["hash_name"] = _hash_name(str(result.get("sha256") or ""), str(result.get("filename") or ""))
    return result


def upsert_app(conn: sqlite3.Connection, *, slug: str, version: str, manifest: dict[str, Any]) -> dict[str, Any]:
    slug = _slug(slug, "app")
    stamp = now()
    conn.execute(
        "INSERT INTO apps(slug,version,manifest_json,installed_at) VALUES (?,?,?,?) "
        "ON CONFLICT(slug) DO UPDATE SET version=excluded.version, manifest_json=excluded.manifest_json",
        (slug, version, json.dumps(manifest, ensure_ascii=False), stamp),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM apps WHERE slug=?", (slug,)).fetchone()
    return dict(row)
