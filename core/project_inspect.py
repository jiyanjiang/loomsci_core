"""Read-only schema inspection for databases owned by reference projects."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

from core import project_store, storage


def _schema_hash(payload: list[dict[str, Any]]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _sqlite(path: Path) -> list[dict[str, Any]]:
    conn = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        tables = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
        result = []
        for table in tables:
            columns = [
                {"name": row[1], "type": row[2], "nullable": not bool(row[3]), "default": row[4]}
                for row in conn.execute(f'PRAGMA table_info("{table}")')
            ]
            try:
                rows = int(conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
            except sqlite3.Error:
                rows = None
            result.append({"name": table, "columns": columns, "rows": rows})
        return result
    finally:
        conn.close()


def _duckdb(path: Path) -> list[dict[str, Any]]:
    try:
        import duckdb  # type: ignore
    except ImportError:
        return [{"error": "duckdb module not installed"}]
    conn = duckdb.connect(str(path), read_only=True)
    try:
        tables = [row[0] for row in conn.execute("SHOW TABLES").fetchall()]
        result = []
        for table in tables:
            columns = [
                {"name": row[0], "type": row[1], "nullable": row[2]}
                for row in conn.execute(f'DESCRIBE "{table}"').fetchall()
            ]
            try:
                rows = int(conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
            except Exception:
                rows = None
            result.append({"name": table, "columns": columns, "rows": rows})
        return result
    finally:
        conn.close()


def inspect_database(path: Path) -> tuple[str, list[dict[str, Any]], str]:
    suffix = path.suffix.lower()
    if suffix == ".duckdb":
        engine = "duckdb"
        tables = _duckdb(path)
    elif suffix in {".db", ".sqlite", ".sqlite3"}:
        engine = "sqlite"
        tables = _sqlite(path)
    else:
        engine = "unknown"
        tables = []
    return engine, tables, _schema_hash(tables)


def inspect_project(conn, code: str) -> dict[str, Any]:
    project = project_store.get_project(conn, code)
    if project is None:
        raise LookupError("project not found")
    stamp = storage.now()
    for source in project["sources"]:
        root = Path(source["root_path"])
        rows = conn.execute(
            "SELECT path, kind FROM project_entries WHERE source_id=? AND kind='db' ORDER BY path",
            (source["id"],),
        ).fetchall()
        for row in rows:
            path = root / row["path"]
            if not path.is_file():
                continue
            try:
                engine, tables, schema_hash = inspect_database(path)
            except Exception as exc:  # noqa: BLE001 - inspection is best effort
                engine, tables, schema_hash = "unknown", [{"error": type(exc).__name__}], ""
            conn.execute(
                "INSERT INTO project_schemas(project_id, source_id, db_path, engine, schema_hash, tables_json, row_json, inspected_at) "
                "VALUES (?,?,?,?,?,?,?,?) "
                "ON CONFLICT(source_id, db_path) DO UPDATE SET engine=excluded.engine, "
                "schema_hash=excluded.schema_hash, tables_json=excluded.tables_json, "
                "row_json=excluded.row_json, inspected_at=excluded.inspected_at",
                (
                    project["id"], source["id"], row["path"], engine, schema_hash,
                    json.dumps(tables, ensure_ascii=False),
                    json.dumps({item.get("name"): item.get("rows") for item in tables if isinstance(item, dict)}, ensure_ascii=False),
                    stamp,
                ),
            )
    conn.commit()
    return project_store.get_project(conn, code) or project
