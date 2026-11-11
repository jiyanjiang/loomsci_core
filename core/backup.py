"""Read-only asset inventory for the P2.5 backup boundary.

This module deliberately does not create or delete files. It classifies the
home into authored/generated assets, third-party references, derived/cache
data, and secrets.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
from pathlib import Path
from typing import Any, Iterator

SKIP_PARTS = {
    ".git", ".cache", ".DS_Store", "__pycache__", "node_modules", "venv",
    ".venv", "core", "cli", "docs", "scripts", "releases", "logs", "runtime",
    "tmp", "temp", "dist", "build",
}
SECRET_NAMES = {".key", ".token", ".pwprofile", ".env", "id_rsa", "id_ed25519"}
SECRET_SUFFIXES = {".key", ".pem", ".p12", ".pfx"}
REFERENCE_SUFFIXES = {
    ".pdf", ".epub", ".mobi", ".djvu", ".doc", ".docx", ".xls", ".xlsx",
    ".zip", ".7z", ".rar", ".tar", ".gz", ".bz2", ".xz", ".csv", ".parquet",
    ".ipynb",
}
TEXT_SUFFIXES = {
    ".md", ".markdown", ".txt", ".json", ".yaml", ".yml", ".toml", ".py",
    ".js", ".ts", ".tsx", ".jsx", ".css", ".html", ".htm", ".sql", ".sh",
}
SECRET_PATTERNS = (
    ("private_key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("openai_key", re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b")),
    ("anthropic_key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{16,}\b")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("generic_secret", re.compile(r"(?i)\b(api[_-]?key|secret|password|passwd|token)\b\s*[:=]\s*[\"']?[^\s\"']{8,}")),
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except (OSError, ValueError):
        return False


def _is_secret_name(path: Path) -> bool:
    return path.name in SECRET_NAMES or path.suffix.lower() in SECRET_SUFFIXES


def _attachment_suffixes(home: Path) -> dict[str, str]:
    db = home / "data" / "data.db"
    if not db.is_file():
        return {}
    conn = None
    try:
        conn = sqlite3.connect(f"file:{db.resolve().as_posix()}?mode=ro", uri=True)
        rows = conn.execute("SELECT id, filename, content_type FROM attachments").fetchall()
    except sqlite3.Error:
        return {}
    finally:
        if conn is not None:
            conn.close()
    result = {}
    for attachment_id, filename, content_type in rows:
        suffix = Path(str(filename or "")).suffix.lower()
        if suffix in REFERENCE_SUFFIXES or str(content_type or "").lower() in {
            "application/pdf", "application/epub+zip", "application/zip",
            "application/octet-stream",
        }:
            result[str(attachment_id)] = suffix or ".bin"
    return result


def _category(path: Path, home: Path, attachment_suffixes: dict[str, str] | None = None) -> tuple[str, str]:
    rel = path.relative_to(home)
    suffix = path.suffix.lower()
    if _is_secret_name(path):
        return "secret", "secret filename"
    if path == home / "config.yaml":
        return "secret", "configuration may contain credentials"
    if path == home / "data" / "data.db":
        return "asset", "SQLite database"
    if rel.parts[:1] == ("agents",):
        return "asset", "agent persona"
    if rel.parts[:2] == ("data", "blobs"):
        suffix = (attachment_suffixes or {}).get(path.name, suffix)
        if suffix in REFERENCE_SUFFIXES:
            return "reference", "third-party binary"
        return "asset", "attachment"
    if rel.parts[:1] in {("assets",), ("programs",)}:
        return "asset", "user/AI program asset"
    if rel.parts[:1] == ("packs",):
        if len(rel.parts) >= 3 and rel.parts[2] == "data":
            if any(part in {"thumbs", "thumbnails", "cache", "ocr"} for part in rel.parts):
                return "derived", "generated cache"
            if suffix in REFERENCE_SUFFIXES:
                return "reference", "third-party binary"
            return "asset", "add-on data"
        return "excluded", "add-on code"
    if rel.parts[:1] == ("data",):
        return "excluded", "data directory"
    return "excluded", "not a backup asset"


def _walk(root: Path) -> Iterator[Path]:
    if not root.is_dir():
        return
    for current, dirs, files in os.walk(root):
        dirs[:] = [name for name in dirs if name not in SKIP_PARTS and not name.startswith(".")]
        for name in files:
            path = Path(current) / name
            if path.is_symlink() or not path.is_file():
                continue
            yield path


def _iter_candidates(home: Path) -> Iterator[Path]:
    seen: set[Path] = set()
    roots = [
        home / "data" / "data.db",
        home / "config.yaml",
        home / "agents",
        home / "data" / "blobs",
        home / "assets",
        home / "programs",
    ]
    packs = home / "packs"
    if packs.is_dir():
        roots.extend(path / "data" for path in packs.iterdir() if path.is_dir())
    for root in roots:
        if root.is_file():
            paths = [root]
        else:
            paths = _walk(root)
        for path in paths:
            if path in seen or not _inside(path, home):
                continue
            seen.add(path)
            yield path


def _scan_text(text: str, location: str) -> list[dict[str, str]]:
    hits = []
    for kind, pattern in SECRET_PATTERNS:
        if pattern.search(text):
            hits.append({"kind": kind, "location": location})
    return hits


def _scan_file(path: Path, home: Path) -> list[dict[str, str]]:
    rel = path.relative_to(home).as_posix()
    if _is_secret_name(path) or path == home / "config.yaml":
        return [{"kind": "secret_file", "location": rel}]
    if path.suffix.lower() not in TEXT_SUFFIXES or path.stat().st_size > 1024 * 1024:
        return []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    return _scan_text(text, rel)


def _scan_db(db: Path) -> list[dict[str, str]]:
    if not db.is_file():
        return []
    conn = None
    try:
        conn = sqlite3.connect(f"file:{db.resolve().as_posix()}?mode=ro", uri=True)
        hits = []
        for table, columns in {
            "posts": ("id", "title", "body"),
            "tasks": ("id", "title", "description", "acceptance"),
            "facts": ("id", "claim", "evidence", "source"),
        }.items():
            try:
                rows = conn.execute(f"SELECT {', '.join(columns)} FROM {table}").fetchall()
            except sqlite3.Error:
                continue
            for row in rows:
                for column, value in zip(columns, row):
                    if isinstance(value, str):
                        hits.extend(_scan_text(value, f"{table}/{row[0]}/{column}"))
        return hits
    except sqlite3.Error:
        return []
    finally:
        if conn is not None:
            conn.close()


def inspect(home: str | Path) -> dict[str, Any]:
    home = Path(home).expanduser()
    summary = {
        "assets": {"files": 0, "bytes": 0},
        "references": {"files": 0, "bytes": 0},
        "derived": {"files": 0, "bytes": 0},
        "excluded": {"files": 0, "bytes": 0},
        "secrets": {"files": 0, "bytes": 0, "hits": 0},
    }
    samples: dict[str, list[dict[str, Any]]] = {key: [] for key in summary}
    secret_hits: list[dict[str, str]] = []
    hashes: dict[str, list[dict[str, Any]]] = {}

    attachment_suffixes = _attachment_suffixes(home)
    for path in _iter_candidates(home):
        try:
            size = path.stat().st_size
        except OSError:
            continue
        category, reason = _category(path, home, attachment_suffixes)
        key = {"asset": "assets", "reference": "references", "derived": "derived", "secret": "secrets"}.get(category, "excluded")
        summary[key]["files"] += 1
        summary[key]["bytes"] += size
        if key != "secrets" and len(samples[key]) < 50:
            samples[key].append({
                "path": path.relative_to(home).as_posix(),
                "bytes": size,
                "reason": reason,
            })
        hits = _scan_file(path, home)
        if hits:
            summary["secrets"]["hits"] += len(hits)
            if key != "secrets":
                summary["secrets"]["files"] += 1
            secret_hits.extend(hits[:20])
        if category == "asset" and path.suffix.lower() not in TEXT_SUFFIXES:
            digest = _sha256(path)
            hashes.setdefault(digest, []).append({
                "path": path.relative_to(home).as_posix(),
                "bytes": size,
            })

    db_hits = _scan_db(home / "data" / "data.db")
    if db_hits:
        summary["secrets"]["hits"] += len(db_hits)
        secret_hits.extend(db_hits[:50])

    duplicates = []
    reclaimable = 0
    for digest, files in hashes.items():
        if len(files) > 1:
            reclaimable += sum(item["bytes"] for item in files[:-1])
            duplicates.append({"sha256": digest, "count": len(files), "bytes": sum(item["bytes"] for item in files), "files": files[:20]})

    warnings = []
    if summary["references"]["files"]:
        warnings.append("third-party binaries are indexed but excluded from the asset backup")
    if summary["derived"]["files"]:
        warnings.append("derived/cache files are excluded")
    if secret_hits:
        warnings.append("secret-like content found; backup export must be blocked or redacted")

    return {
        "ok": True,
        "home": str(home),
        "summary": summary,
        "duplicates": duplicates,
        "reclaimable_bytes": reclaimable,
        "secret_hits": secret_hits,
        "samples": samples,
        "warnings": warnings,
    }
