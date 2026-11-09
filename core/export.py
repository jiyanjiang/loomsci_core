"""Portable export/import for the Core home.

The export is a zip with a manifest, a JSON data snapshot, agent files, and
content-addressed blobs. Import only accepts safe relative members and verifies
record counts after inserting.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from core import storage
from core.home import ensure_layout

FORMAT = "loomsci_core_export"
VERSION = 1
MAX_ZIP_BYTES = 200 * 1024 * 1024
MAX_MEMBERS = 10_000
TABLES = ("agents", "agent_aliases", "posts", "tasks", "reads", "presence")
COLUMNS = {
    "agents": ("handle", "kind", "created_at"),
    "agent_aliases": ("alias", "handle", "created_at"),
    "posts": (
        "seq", "id", "thread_id", "parent_id", "author", "kind", "title",
        "body", "meta_json", "created_at",
    ),
    "tasks": (
        "id", "title", "description", "acceptance", "status", "assigned_to",
        "claimed_at", "lease_until", "evidence_json", "created_at", "updated_at",
    ),
    "reads": ("agent", "scope", "last_seq", "updated_at"),
    "presence": (
        "agent", "tool", "workspace", "model", "pid", "started_at", "last_seen",
    ),
}
AGENT_SKIP_PARTS = {
    "__pycache__", ".git", ".key", ".token", ".pwprofile", ".cache",
    ".DS_Store", "memory.db-wal", "memory.db-shm",
}
SENSITIVE_PARTS = {
    ".key", ".token", ".pwprofile", ".cache", ".env", ".env.local",
    "id_rsa", "id_ed25519",
}


class ExportError(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _rows(conn: sqlite3.Connection, table: str) -> list[dict[str, Any]]:
    columns = COLUMNS[table]
    sql = f"SELECT {', '.join(columns)} FROM {table}"
    return [dict(row) for row in conn.execute(sql).fetchall()]


def _counts(conn: sqlite3.Connection) -> dict[str, int]:
    result = {}
    for table in TABLES:
        try:
            result[table] = int(
                conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            )
        except sqlite3.Error:
            result[table] = 0
    return result


def _agent_files(home: Path) -> list[Path]:
    root = home / "agents"
    if not root.is_dir():
        return []
    result = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in AGENT_SKIP_PARTS for part in path.parts):
            continue
        result.append(path)
    return sorted(result)


def export_home(home: str | Path, out_path: str | Path) -> dict[str, Any]:
    home = Path(home).expanduser()
    out = Path(out_path).expanduser()
    layout = ensure_layout(home)
    if not layout.db.is_file():
        raise ExportError("database not found")
    conn = storage.connect(layout.db)
    try:
        data = {table: _rows(conn, table) for table in TABLES}
        counts = _counts(conn)
    finally:
        conn.close()

    out.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix="loomsci-export-", suffix=".zip")
    os.close(fd)
    tmp = Path(tmp_name)
    files: list[dict[str, Any]] = []
    try:
        with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for path in _agent_files(home):
                rel = path.relative_to(home).as_posix()
                zf.write(path, rel)
                files.append({"path": rel, "bytes": path.stat().st_size,
                              "sha256": _sha256(path)})
            blobs = layout.data / "blobs"
            if blobs.is_dir():
                for path in sorted(blobs.rglob("*")):
                    if not path.is_file():
                        continue
                    rel = "blobs/" + path.relative_to(blobs).as_posix()
                    zf.write(path, rel)
                    files.append({"path": rel, "bytes": path.stat().st_size,
                                  "sha256": _sha256(path)})
            zf.writestr("data.json", json.dumps(data, ensure_ascii=False, indent=2))
            manifest = {
                "format": FORMAT,
                "version": VERSION,
                "created_at": _now(),
                "counts": counts,
                "files": files,
            }
            zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        os.replace(tmp, out)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
    return {"ok": True, "path": str(out), "counts": counts, "files": len(files)}


def _safe_member(name: str) -> bool:
    if not name or name.startswith("/") or "\\" in name:
        return False
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts:
        return False
    if ":" in path.parts[0]:
        return False
    return True


def _read_json(zf: zipfile.ZipFile, name: str) -> Any:
    info = zf.getinfo(name)
    if info.file_size > 10 * 1024 * 1024:
        raise ExportError(f"{name} is too large")
    with zf.open(info) as fh:
        return json.loads(fh.read().decode("utf-8"))


def _insert(conn: sqlite3.Connection, table: str, rows: list[dict[str, Any]]) -> None:
    columns = COLUMNS[table]
    sql = (
        f"INSERT INTO {table}({', '.join(columns)}) "
        f"VALUES ({', '.join('?' for _ in columns)})"
    )
    for row in rows:
        conn.execute(sql, tuple(row.get(column) for column in columns))


def import_home(zip_path: str | Path, destination: str | Path) -> dict[str, Any]:
    source = Path(zip_path).expanduser()
    dest = Path(destination).expanduser()
    if not source.is_file():
        raise ExportError("export file not found")
    if source.stat().st_size > MAX_ZIP_BYTES:
        raise ExportError("export file is too large")
    if dest.exists() and any(dest.iterdir()):
        raise ExportError(f"destination is not empty: {dest}")

    with zipfile.ZipFile(source, "r") as zf:
        infos = zf.infolist()
        if len(infos) > MAX_MEMBERS:
            raise ExportError("too many zip members")
        total = sum(info.file_size for info in infos)
        if total > MAX_ZIP_BYTES:
            raise ExportError("uncompressed export is too large")
        for info in infos:
            if not _safe_member(info.filename):
                raise ExportError(f"unsafe zip member: {info.filename}")
            if any(part in SENSITIVE_PARTS for part in PurePosixPath(info.filename).parts):
                raise ExportError(f"sensitive file not allowed: {info.filename}")
            mode = (info.external_attr >> 16) & 0o170000
            if mode == 0o120000:
                raise ExportError(f"symlink not allowed: {info.filename}")

        manifest = _read_json(zf, "manifest.json")
        if manifest.get("format") != FORMAT or int(manifest.get("version", 0)) != VERSION:
            raise ExportError("unsupported export format")
        data = _read_json(zf, "data.json")
        if not isinstance(data, dict):
            raise ExportError("data.json must be an object")

        layout = ensure_layout(dest)
        storage.init_db(layout.db)
        conn = storage.connect(layout.db)
        try:
            conn.execute("BEGIN")
            for table in TABLES:
                rows = data.get(table) or []
                if not isinstance(rows, list):
                    raise ExportError(f"{table} must be a list")
                _insert(conn, table, rows)
            conn.commit()
            counts = _counts(conn)
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

        expected = manifest.get("counts") or {}
        for table, value in expected.items():
            if counts.get(table, 0) != int(value):
                raise ExportError(
                    f"count mismatch for {table}: {counts.get(table, 0)} != {value}"
                )

        for info in infos:
            if info.filename in {"manifest.json", "data.json"}:
                continue
            relative = PurePosixPath(info.filename)
            if relative.parts[0] == "agents":
                target = dest / relative
            elif relative.parts[0] == "blobs":
                target = layout.data / relative
            else:
                raise ExportError(f"unexpected export member: {info.filename}")
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, target.open("wb") as dst:
                while True:
                    chunk = src.read(1024 * 1024)
                    if not chunk:
                        break
                    dst.write(chunk)

    return {"ok": True, "path": str(dest), "counts": counts}
