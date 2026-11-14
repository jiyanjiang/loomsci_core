#!/usr/bin/env python3
"""Apply prototype: beta.28 -> Core v0 + Report/Project app DBs.

Not product code. Source is opened read-only; output is a new workspace.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import shutil
import sqlite3
import time
from pathlib import Path

ARCHIVE = ("post_summaries", "mentions", "reads", "presence", "agents", "agent_aliases", "tag_aliases", "schema_migrations")
PROJECT_TABLES = ("projects", "project_sources", "project_entries", "project_schemas", "project_apps", "project_evaluations", "tasks")


def _ro(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _count(conn: sqlite3.Connection, table: str) -> int:
    return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def _create_like(dst: sqlite3.Connection, source: sqlite3.Connection, table: str) -> None:
    columns = source.execute(f"PRAGMA table_info({table})").fetchall()
    if not columns:
        return
    definitions = []
    for column in columns:
        name = column["name"]
        kind = column["type"] or "TEXT"
        definitions.append(f'"{name}" {kind}')
    dst.execute(f'CREATE TABLE IF NOT EXISTS "{table}" ({", ".join(definitions)})')


def _copy_table(source: sqlite3.Connection, dst: sqlite3.Connection, table: str) -> int:
    _create_like(dst, source, table)
    rows = source.execute(f'SELECT * FROM "{table}"').fetchall()
    if not rows:
        return 0
    columns = [key for key in rows[0].keys()]
    placeholders = ",".join("?" for _ in columns)
    names = ",".join(f'"{name}"' for name in columns)
    dst.executemany(
        f'INSERT INTO "{table}" ({names}) VALUES ({placeholders})',
        [tuple(row[name] for name in columns) for row in rows],
    )
    return len(rows)


def _export_jsonl(source: sqlite3.Connection, table: str, target: Path) -> int:
    if not source.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone():
        return 0
    rows = source.execute(f'SELECT * FROM "{table}"').fetchall()
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(dict(row), ensure_ascii=False, sort_keys=True) + "\n")
    return len(rows)


def _core_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
    CREATE TABLE items (
      id TEXT PRIMARY KEY, app TEXT NOT NULL, type TEXT NOT NULL,
      title TEXT, body TEXT, metadata_json TEXT NOT NULL DEFAULT '{}',
      created_at TEXT NOT NULL, updated_at TEXT NOT NULL
    );
    CREATE TABLE item_tags (
      item_id TEXT NOT NULL, tag TEXT NOT NULL, source TEXT NOT NULL DEFAULT 'ai',
      confidence REAL, PRIMARY KEY (item_id, tag)
    );
    CREATE TABLE blobs (
      id TEXT PRIMARY KEY, item_id TEXT, filename TEXT NOT NULL,
      content_type TEXT, bytes INTEGER NOT NULL, sha256 TEXT NOT NULL,
      created_at TEXT NOT NULL
    );
    CREATE TABLE apps (
      slug TEXT PRIMARY KEY, version TEXT NOT NULL,
      manifest_json TEXT NOT NULL, installed_at TEXT NOT NULL
    );
    CREATE VIRTUAL TABLE items_fts USING fts5(
      id UNINDEXED, title, body, tags, app, tokenize='unicode61'
    );
    """)


def _report_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
    CREATE TABLE notes (
      item_id TEXT PRIMARY KEY, legacy_kind TEXT, legacy_author TEXT,
      thread_id TEXT, parent_id TEXT, legacy_meta_json TEXT, created_at TEXT
    );
    """)


def apply(source_home: Path, target_home: Path) -> dict:
    source_db = source_home / "data" / "data.db"
    if not source_db.is_file():
        raise SystemExit(f"source DB missing: {source_db}")
    if target_home.exists():
        raise SystemExit(f"target already exists: {target_home}")
    tmp = target_home.with_name(target_home.name + ".tmp-" + str(os.getpid()))
    if tmp.exists():
        shutil.rmtree(tmp)
    source_hash_before = _hash(source_db)
    try:
        (tmp / "data" / "blobs").mkdir(parents=True)
        (tmp / "apps" / "report" / "data").mkdir(parents=True)
        (tmp / "apps" / "project" / "data").mkdir(parents=True)
        src = _ro(source_db)
        core = sqlite3.connect(tmp / "data" / "core.db")
        report = sqlite3.connect(tmp / "apps" / "report" / "data" / "report.db")
        project = sqlite3.connect(tmp / "apps" / "project" / "data" / "project.db")
        _core_schema(core)
        _report_schema(report)
        stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        for row in src.execute("SELECT * FROM posts"):
            meta = {
                "legacy_kind": row["kind"],
                "legacy_author": row["author"],
                "thread_id": row["thread_id"],
                "parent_id": row["parent_id"],
                "legacy_meta": json.loads(row["meta_json"]) if row["meta_json"] else {},
                "source": "beta.28",
            }
            core.execute(
                "INSERT INTO items VALUES (?,?,?,?,?,?,?,?)",
                (row["id"], "report", "report.note", "", row["body"],
                 json.dumps(meta, ensure_ascii=False), row["created_at"], row["created_at"]),
            )
            report.execute(
                "INSERT INTO notes VALUES (?,?,?,?,?,?,?)",
                (row["id"], row["kind"], row["author"], row["thread_id"],
                 row["parent_id"], row["meta_json"], row["created_at"]),
            )

        # attachments/blobs
        for row in src.execute("SELECT * FROM attachments"):
            target = tmp / "data" / "blobs" / row["id"]
            blob = source_home / "data" / "blobs" / row["id"]
            if blob.is_file():
                shutil.copy2(blob, target)
                if _hash(target) != row["sha256"] or target.stat().st_size != row["bytes"]:
                    raise SystemExit(f"blob mismatch: {row['id']}")
            core.execute(
                "INSERT INTO blobs VALUES (?,?,?,?,?,?,?)",
                (row["id"], row["post_id"], row["filename"], row["content_type"],
                 row["bytes"], row["sha256"], row["created_at"]),
            )

        # tags
        if src.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='post_tags'").fetchone():
            for row in src.execute(
                "SELECT pt.post_id, t.name, pt.source, pt.confidence "
                "FROM post_tags pt JOIN tags t ON t.id=pt.tag_id"
            ):
                core.execute(
                    "INSERT OR IGNORE INTO item_tags(item_id,tag,source,confidence) VALUES (?,?,?,?)",
                    (row["post_id"], row["name"], row["source"], row["confidence"]),
                )

        # facts
        for row in src.execute("SELECT * FROM facts"):
            meta = {
                "project": row["project"],
                "source": row["source"],
                "status": row["status"],
                "confidence": row["confidence"],
                "created_by": row["created_by"],
                "reviewed_by": row["reviewed_by"],
                "legacy_tags": row["tags"],
            }
            core.execute(
                "INSERT INTO items VALUES (?,?,?,?,?,?,?,?)",
                (row["id"], "project", "project.fact", row["claim"], row["evidence"] or "",
                 json.dumps(meta, ensure_ascii=False), row["created_at"], row["updated_at"]),
            )

        # project DB tables + project projection
        for table in PROJECT_TABLES:
            if src.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone():
                _copy_table(src, project, table)
        for row in src.execute("SELECT * FROM projects"):
            meta = {
                key: row[key] for key in (
                    "code", "type", "status", "machine_id", "review_status",
                    "completeness", "maturity", "commercial_potential", "direction",
                    "review_notes", "reviewed_at", "reviewed_by",
                )
            }
            core.execute(
                "INSERT INTO items VALUES (?,?,?,?,?,?,?,?)",
                ("project:" + row["id"], "project", "project.project", row["name"],
                 row["description"] or "", json.dumps(meta, ensure_ascii=False),
                 row["created_at"], row["updated_at"]),
            )

        # legacy archive
        for table in ARCHIVE:
            _export_jsonl(src, table, tmp / "legacy" / f"{table}.jsonl")

        # FTS
        core.execute(
            "INSERT INTO items_fts(id,title,body,tags,app) "
            "SELECT i.id,i.title,i.body,COALESCE((SELECT group_concat(tag,' ') FROM item_tags t WHERE t.item_id=i.id),''),i.app "
            "FROM items i"
        )
        core.commit(); report.commit(); project.commit()
        apps = {
            "report": {"version": "prototype"},
            "project": {"version": "prototype"},
        }
        (tmp / "apps" / "installed.json").write_text(json.dumps(apps), encoding="utf-8")
        (tmp / "local.token").write_text(secrets.token_hex(32) + "\n", encoding="utf-8")
        (tmp / "local.token").chmod(0o600)
        counts = {
            "items": _count(core, "items"),
            "report.note": core.execute("SELECT COUNT(*) FROM items WHERE type='report.note'").fetchone()[0],
            "project.fact": core.execute("SELECT COUNT(*) FROM items WHERE type='project.fact'").fetchone()[0],
            "project.project": core.execute("SELECT COUNT(*) FROM items WHERE type='project.project'").fetchone()[0],
            "blobs": _count(core, "blobs"),
            "project_entries": _count(project, "project_entries"),
            "tasks": _count(project, "tasks"),
        }
        search = core.execute("SELECT COUNT(*) FROM items_fts WHERE items_fts MATCH 'beta'").fetchone()[0]
        src.close(); core.close(); report.close(); project.close()
        if _hash(source_db) != source_hash_before:
            raise SystemExit("source changed")
        report_data = {
            "format": "loomsci-migration/1",
            "source": str(source_home),
            "source_sha256": source_hash_before,
            "created_at": stamp,
            "counts": counts,
            "fts_beta_hits": search,
        }
        (tmp / "migration-report.json").write_text(json.dumps(report_data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.rename(target_home)
        return report_data
    except Exception:
        if tmp.exists():
            shutil.rmtree(tmp)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--from", dest="source", required=True)
    parser.add_argument("--to", dest="target", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    source = Path(args.source).expanduser()
    target = Path(args.target).expanduser()
    if not args.apply:
        db = source / "data" / "data.db"
        conn = _ro(db)
        try:
            counts = {}
            for table in ("posts", "attachments", "facts", "projects", "project_entries", "tasks"):
                if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone():
                    counts[table] = _count(conn, table)
            print(json.dumps({"dry_run": True, "source": str(source), "counts": counts}, ensure_ascii=False, indent=2))
            return 0
        finally:
            conn.close()
    print(json.dumps(apply(source, target), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
