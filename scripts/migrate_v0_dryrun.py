#!/usr/bin/env python3
"""Read-only dry-run inventory for the beta.28 -> Core v0 migration."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

MAPPED = {
    "posts": "core.items (report.note)",
    "attachments": "core.blobs",
    "tags": "core.item_tags",
    "post_tags": "core.item_tags",
    "facts": "core.items (project.fact)",
    "projects": "project app DB + core projection",
    "project_sources": "project app DB",
    "project_entries": "project app DB",
    "project_schemas": "project app DB",
    "project_apps": "project app DB",
    "project_evaluations": "project app DB",
    "tasks": "project app DB",
}
ARCHIVED = {
    "post_summaries",
    "mentions",
    "reads",
    "presence",
    "tag_aliases",
    "schema_migrations",
    "agents",
    "agent_aliases",
}
IGNORED = {"sqlite_sequence"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--from", dest="source", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    home = Path(args.source).expanduser()
    db = home / "data" / "data.db"
    if not db.is_file():
        raise SystemExit(f"source DB missing: {db}")
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE '%_fts%'"
            )
        }
        counts = {}
        for table in sorted(tables - IGNORED):
            try:
                counts[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            except sqlite3.Error:
                counts[table] = None
        blob_dir = home / "data" / "blobs"
        blobs = 0
        blob_bytes = 0
        if blob_dir.is_dir():
            for path in blob_dir.iterdir():
                if path.is_file():
                    blobs += 1
                    blob_bytes += path.stat().st_size
        result = {
            "source": str(home),
            "db": str(db),
            "counts": counts,
            "mapped": {table: MAPPED[table] for table in sorted(tables & set(MAPPED))},
            "archived": sorted(tables & ARCHIVED),
            "unmapped": sorted(tables - set(MAPPED) - ARCHIVED - IGNORED),
            "blobs": {"files": blobs, "bytes": blob_bytes},
            "estimated_target_bytes": blob_bytes + (db.stat().st_size // 2),
            "dry_run": True,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
