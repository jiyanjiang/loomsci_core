"""Local reference projects and metadata indexes.

Projects point at source paths. This module never copies source files.
"""

from __future__ import annotations

import fnmatch
import os
import re
import secrets
import socket
import urllib.error
import urllib.request
from urllib.parse import urlsplit
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from core import storage

DEFAULT_EXCLUDES = {
    ".git", ".hg", ".svn", "node_modules", "venv", ".venv", "__pycache__",
    ".cache", "site-packages", ".pytest_cache", ".mypy_cache",
}
MAX_FILES = 100_000
KIND_BY_SUFFIX = {
    ".md": "doc", ".markdown": "doc", ".txt": "doc", ".rst": "doc",
    ".py": "code", ".js": "code", ".ts": "code", ".tsx": "code", ".jsx": "code",
    ".duckdb": "db", ".db": "db", ".sqlite": "db", ".sqlite3": "db",
    ".parquet": "data", ".csv": "data", ".json": "data",
}


def _now() -> str:
    return storage.now()


def _date(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()


def _machine_id() -> str:
    return socket.gethostname() or "local"


def _excluded(name: str, patterns: Iterable[str]) -> bool:
    return name in DEFAULT_EXCLUDES or any(fnmatch.fnmatch(name, p) for p in patterns)


def _title(path: Path) -> tuple[str, str]:
    if path.suffix.lower() not in {".md", ".markdown"}:
        return "", ""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")[:8192]
    except OSError:
        return "", ""
    lines = [line.strip() for line in text.splitlines()]
    title = next((line[2:].strip() for line in lines if line.startswith("# ")), "")
    body = []
    started = bool(title)
    for line in lines:
        if not started:
            continue
        if line.startswith("#"):
            break
        if not line:
            if body:
                break
            continue
        body.append(line)
    return title, " ".join(body)[:240].strip()


def _walk(source: Path, exclude: Iterable[str]) -> tuple[list[dict[str, Any]], str, int]:
    entries: list[dict[str, Any]] = []
    latest = 0.0
    total = 0
    if not source.is_dir():
        return entries, "", 0
    for dirpath, dirs, files in os.walk(source, followlinks=False):
        dirs[:] = [d for d in dirs if not _excluded(d, exclude)]
        for name in files:
            if len(entries) >= MAX_FILES:
                return entries, _date(latest) if latest else "", total
            path = Path(dirpath) / name
            try:
                stat = path.stat()
            except OSError:
                continue
            rel = str(path.relative_to(source))
            suffix = path.suffix.lower()
            kind = KIND_BY_SUFFIX.get(suffix, "other")
            title, summary = _title(path)
            entries.append({
                "path": rel,
                "kind": kind,
                "title": title,
                "bytes": stat.st_size,
                "mtime": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).replace(microsecond=0).isoformat(),
                "sha256": "",
                "summary": summary,
            })
            latest = max(latest, stat.st_mtime)
            total += stat.st_size
    return entries, _date(latest) if latest else "", total


def _source_dict(row) -> dict[str, Any]:
    item = dict(row)
    try:
        import json
        meta = item.pop("meta_json", "{}")
        item["meta"] = json.loads(meta or "{}")
    except (TypeError, ValueError):
        item["meta"] = {}
    return item


def _project_dict(row) -> dict[str, Any]:
    return dict(row)


def create_project(
    conn,
    *,
    code: str,
    name: str,
    description: str = "",
    project_type: str = "unknown",
    sources: list[dict[str, str]],
    app_port: int | None = None,
    exclude: Iterable[str] = (),
) -> dict[str, Any]:
    code = str(code or "").strip().lower() or "project"
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", code):
        raise ValueError("code must be lowercase letters/digits/hyphen")
    if not sources:
        raise ValueError("at least one source is required")
    stamp = _now()
    project_id = "pr-" + secrets.token_hex(6)
    conn.execute(
        "INSERT INTO projects(id, code, name, description, type, status, machine_id, created_at, updated_at) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        (project_id, code, name, description, project_type, "candidate", _machine_id(), stamp, stamp),
    )
    for source in sources:
        role = str(source.get("role") or "code").strip() or "code"
        root = Path(str(source.get("path") or "")).expanduser().resolve()
        entries, data_as_of, total = _walk(root, exclude)
        source_id = "src-" + secrets.token_hex(6)
        state = "available" if root.is_dir() else "missing"
        conn.execute(
            "INSERT INTO project_sources(id, project_id, role, root_path, source_state, data_as_of, last_seen_at, meta_json) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (source_id, project_id, role, str(root), state, data_as_of, stamp, "{}"),
        )
        for entry in entries:
            conn.execute(
                "INSERT INTO project_entries(project_id, source_id, path, kind, title, bytes, mtime, sha256, summary) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (project_id, source_id, entry["path"], entry["kind"], entry["title"] or None,
                 entry["bytes"], entry["mtime"], entry["sha256"], entry["summary"] or None),
            )
        source["_id"] = source_id
        source["_entries"] = len(entries)
        source["_bytes"] = total
    if app_port:
        conn.execute(
            "INSERT INTO project_apps(project_id, source_id, name, command, port, url, status) "
            "VALUES (?,?,?,?,?,?,?)",
            (project_id, sources[0]["_id"], "default", "", int(app_port),
             f"http://127.0.0.1:{int(app_port)}", "registered"),
        )
    conn.commit()
    return get_project(conn, code) or {"id": project_id}


def list_projects(conn, *, selected_only: bool = False) -> list[dict[str, Any]]:
    where = " WHERE p.review_status='selected'" if selected_only else ""
    rows = conn.execute(
        "SELECT p.*, (SELECT COUNT(*) FROM project_sources s WHERE s.project_id=p.id) AS sources, "
        "(SELECT COUNT(*) FROM project_entries e WHERE e.project_id=p.id) AS entries, "
        "(SELECT COALESCE(SUM(bytes),0) FROM project_entries e WHERE e.project_id=p.id) AS bytes "
        "FROM projects p" + where + " ORDER BY p.updated_at DESC"
    ).fetchall()
    return [_project_dict(row) for row in rows]


def get_project(conn, code: str) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM projects WHERE code=?", (str(code),)).fetchone()
    if row is None:
        return None
    project = _project_dict(row)
    project["sources"] = [
        _source_dict(item)
        for item in conn.execute(
            "SELECT * FROM project_sources WHERE project_id=? ORDER BY role", (project["id"],)
        )
    ]
    project["counts"] = {
        "entries": int(conn.execute("SELECT COUNT(*) FROM project_entries WHERE project_id=?", (project["id"],)).fetchone()[0]),
        "bytes": int(conn.execute("SELECT COALESCE(SUM(bytes),0) FROM project_entries WHERE project_id=?", (project["id"],)).fetchone()[0]),
    }
    project["apps"] = [
        dict(item)
        for item in conn.execute("SELECT * FROM project_apps WHERE project_id=? ORDER BY name", (project["id"],))
    ]
    project["schemas"] = [
        dict(item)
        for item in conn.execute("SELECT * FROM project_schemas WHERE project_id=? ORDER BY db_path", (project["id"],))
    ]
    return project


def refresh_project(conn, code: str, exclude: Iterable[str] = ()) -> dict[str, Any]:
    project = get_project(conn, code)
    if project is None:
        raise LookupError("project not found")
    stamp = _now()
    for source in project["sources"]:
        root = Path(source["root_path"])
        entries, data_as_of, _ = _walk(root, exclude)
        conn.execute("DELETE FROM project_entries WHERE source_id=?", (source["id"],))
        for entry in entries:
            conn.execute(
                "INSERT INTO project_entries(project_id, source_id, path, kind, title, bytes, mtime, sha256, summary) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (project["id"], source["id"], entry["path"], entry["kind"], entry["title"] or None,
                 entry["bytes"], entry["mtime"], entry["sha256"], entry["summary"] or None),
            )
        conn.execute(
            "UPDATE project_sources SET source_state=?, data_as_of=?, last_seen_at=? WHERE id=?",
            ("available" if root.is_dir() else "missing", data_as_of, stamp, source["id"]),
        )
    conn.execute("UPDATE projects SET updated_at=? WHERE id=?", (stamp, project["id"]))
    conn.commit()
    return get_project(conn, code) or project


def remove_project(conn, code: str) -> bool:
    row = conn.execute("SELECT id FROM projects WHERE code=?", (str(code),)).fetchone()
    if row is None:
        return False
    project_id = row["id"]
    conn.execute("DELETE FROM project_entries WHERE project_id=?", (project_id,))
    conn.execute("DELETE FROM project_schemas WHERE project_id=?", (project_id,))
    conn.execute("DELETE FROM project_apps WHERE project_id=?", (project_id,))
    conn.execute("DELETE FROM project_sources WHERE project_id=?", (project_id,))
    conn.execute("DELETE FROM projects WHERE id=?", (project_id,))
    conn.commit()
    return True


def entries(
    conn,
    code: str,
    *,
    kind: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    project = get_project(conn, code)
    if project is None:
        raise LookupError("project not found")
    limit = max(1, min(int(limit), 500))
    offset = max(0, int(offset))
    where = ["project_id=?"]
    params: list[Any] = [project["id"]]
    if kind:
        where.append("kind=?")
        params.append(str(kind))
    clause = " AND ".join(where)
    total = int(conn.execute(f"SELECT COUNT(*) FROM project_entries WHERE {clause}", params).fetchone()[0])
    rows = conn.execute(
        f"SELECT path, kind, title, bytes, mtime, summary FROM project_entries "
        f"WHERE {clause} ORDER BY mtime DESC, path LIMIT ? OFFSET ?",
        (*params, limit, offset),
    ).fetchall()
    return {"total": total, "limit": limit, "offset": offset, "entries": [dict(row) for row in rows]}


def stats(conn, code: str) -> dict[str, Any]:
    project = get_project(conn, code)
    if project is None:
        raise LookupError("project not found")
    project_id = project["id"]
    kinds = [
        dict(row)
        for row in conn.execute(
            "SELECT kind, COUNT(*) AS entries, COALESCE(SUM(bytes),0) AS bytes "
            "FROM project_entries WHERE project_id=? GROUP BY kind ORDER BY entries DESC",
            (project_id,),
        )
    ]
    timeline = [
        dict(row)
        for row in conn.execute(
            "SELECT substr(mtime,1,7) AS month, COUNT(*) AS entries, "
            "COALESCE(SUM(bytes),0) AS bytes FROM project_entries "
            "WHERE project_id=? AND mtime IS NOT NULL AND mtime != '' "
            "GROUP BY month ORDER BY month DESC LIMIT 24",
            (project_id,),
        )
    ]
    recent = [
        dict(row)
        for row in conn.execute(
            "SELECT path, kind, title, bytes, mtime FROM project_entries "
            "WHERE project_id=? ORDER BY mtime DESC, path LIMIT 12",
            (project_id,),
        )
    ]
    return {
        "project": project,
        "kinds": kinds,
        "timeline": list(reversed(timeline)),
        "recent": recent,
    }


def review_project(
    conn,
    code: str,
    *,
    review_status: str,
    completeness: int | None = None,
    maturity: int | None = None,
    commercial_potential: int | None = None,
    direction: str = "",
    notes: str = "",
    reviewer: str = "owner",
) -> dict[str, Any]:
    allowed = {"candidate", "reviewed", "selected", "rejected"}
    if review_status not in allowed:
        raise ValueError("invalid review status")
    scores = {
        "completeness": completeness,
        "maturity": maturity,
        "commercial_potential": commercial_potential,
    }
    for name, value in scores.items():
        if value is not None and not 0 <= int(value) <= 5:
            raise ValueError(f"{name} must be 0-5")
    project = get_project(conn, code)
    if project is None:
        raise LookupError("project not found")
    stamp = _now()
    state = {"selected": "active", "rejected": "archived"}.get(review_status, "candidate")
    conn.execute(
        "UPDATE projects SET review_status=?, status=?, completeness=?, maturity=?, "
        "commercial_potential=?, direction=?, review_notes=?, reviewed_at=?, reviewed_by=?, "
        "updated_at=? WHERE id=?",
        (
            review_status, state, completeness, maturity, commercial_potential,
            direction, notes, stamp, reviewer, stamp, project["id"],
        ),
    )
    conn.commit()
    return get_project(conn, code) or project


def add_app(
    conn,
    code: str,
    *,
    name: str,
    command: str = "",
    port: int | None = None,
    url: str = "",
) -> dict[str, Any]:
    project = get_project(conn, code)
    if project is None:
        raise LookupError("project not found")
    if not project["sources"]:
        raise ValueError("project has no source")
    app_name = str(name or "").strip() or "default"
    target = str(url or "").strip()
    if not target and port:
        target = f"http://127.0.0.1:{int(port)}"
    if target:
        parsed = urlsplit(target)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("app URL must be http or https")
        if (parsed.hostname or "").lower() not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("app URL must be loopback")
        if parsed.username or parsed.password:
            raise ValueError("app URL must not contain credentials")
    source_id = project["sources"][0]["id"]
    conn.execute(
        "INSERT INTO project_apps(project_id, source_id, name, command, port, url, status, checked_at, error) "
        "VALUES (?,?,?,?,?,?,?,?,?) "
        "ON CONFLICT(source_id, name) DO UPDATE SET command=excluded.command, "
        "port=excluded.port, url=excluded.url, status=excluded.status, error=excluded.error",
        (project["id"], source_id, app_name, command, int(port) if port else None,
         target, "registered", None, None),
    )
    conn.commit()
    return get_project(conn, code) or project


def check_app(conn, code: str, name: str) -> dict[str, Any]:
    project = get_project(conn, code)
    if project is None:
        raise LookupError("project not found")
    app = next((item for item in project["apps"] if item.get("name") == name), None)
    if app is None:
        raise LookupError("app not found")
    url = str(app.get("url") or "")
    status = "registered"
    error = None
    if url:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                status = "running" if 200 <= response.status < 400 else "unreachable"
        except (OSError, ValueError, urllib.error.URLError):
            status = "unreachable"
            error = "unreachable"
    stamp = _now()
    conn.execute(
        "UPDATE project_apps SET status=?, checked_at=?, error=? WHERE source_id=? AND name=?",
        (status, stamp, error, app["source_id"], name),
    )
    conn.commit()
    project = get_project(conn, code) or project
    return next(item for item in project["apps"] if item.get("name") == name)


def check_all_apps(conn, code: str) -> list[dict[str, Any]]:
    project = get_project(conn, code)
    if project is None:
        raise LookupError("project not found")
    return [check_app(conn, code, item["name"]) for item in project["apps"]]
