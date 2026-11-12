"""Read-only project discovery.

This module never copies or executes project content. It records paths, marker
files, counts, and small README excerpts for user review.
"""

from __future__ import annotations

import fnmatch
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

STRONG_FILES = {
    "pyproject.toml", "package.json", "Cargo.toml", "go.mod",
    "project.yaml", "project.yml", "project.json",
}
README_FILES = ("README.md", "README.zh-CN.md", "readme.md", "README.rst")
DB_SUFFIXES = {".db", ".sqlite", ".sqlite3", ".duckdb"}
DEFAULT_EXCLUDES = {
    ".git", ".hg", ".svn", "node_modules", "venv", ".venv", "__pycache__",
    ".cache", "site-packages", ".pytest_cache", ".mypy_cache",
}
MAX_FILES = 50_000
MAX_README = 64 * 1024
SNAPSHOT_RE = re.compile(r"(?:^|/)share_.*_v\d+$|(?:^|/)v\d+$")


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:60] or "project"


def _date(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).date().isoformat()


def _excluded(name: str, patterns: Iterable[str]) -> bool:
    return name in DEFAULT_EXCLUDES or any(fnmatch.fnmatch(name, p) for p in patterns)


def _markers(path: Path) -> tuple[list[str], list[str], int]:
    try:
        entries = list(os.scandir(path))
    except OSError:
        return [], [], 0
    names = {entry.name for entry in entries if entry.is_file(follow_symlinks=False)}
    dirs = {entry.name for entry in entries if entry.is_dir(follow_symlinks=False)}
    evidence = []
    score = 0
    if names & STRONG_FILES:
        evidence.append("strong-manifest")
        score += 4
    if ".git" in dirs:
        evidence.append("git")
        score += 2
    readme = next((name for name in README_FILES if name in names), "")
    if readme:
        evidence.append("readme")
        score += 1
    if "requirements.txt" in names:
        evidence.append("requirements")
        score += 1
    if "docs" in dirs:
        evidence.append("docs")
        score += 1
    if any(name in dirs for name in ("scripts", "src", "lib", "web", "app", "plan", "data")):
        evidence.append("structure")
        score += 1
    if any(entry.name.lower().endswith(tuple(DB_SUFFIXES)) for entry in entries):
        evidence.append("database")
        score += 2
    return sorted(evidence), sorted(names), score


def _readme(path: Path, names: list[str]) -> tuple[str, str]:
    name = next((name for name in README_FILES if name in names), "")
    if not name:
        return "", ""
    try:
        text = (path / name).read_text(encoding="utf-8", errors="replace")[:MAX_README]
    except OSError:
        return "", ""
    lines = [line.strip() for line in text.splitlines()]
    heading = next((line.lstrip("# ").strip() for line in lines if line.startswith("# ")), "")
    body = []
    started = bool(heading)
    for line in lines:
        if not started:
            continue
        if not line:
            if body:
                break
            continue
        if line.startswith("#"):
            break
        if not body and line.startswith("#"):
            continue
        body.append(line)
    if not body:
        candidate = " ".join(line for line in lines if line and not line.startswith("#"))
        body = [candidate[:300]]
    return heading, " ".join(body)[:300].strip()


def _stats(root: Path, *, exclude: Iterable[str]) -> dict[str, Any]:
    counts = {"files": 0, "md": 0, "py": 0, "js": 0, "db": 0, "parquet": 0}
    bytes_total = 0
    latest = 0.0
    db_files: list[dict[str, Any]] = []
    snapshots: list[str] = []
    truncated = False
    try:
        top = [entry for entry in os.scandir(root) if entry.is_dir(follow_symlinks=False)]
    except OSError:
        top = []
    for entry in top:
        if SNAPSHOT_RE.search(entry.name):
            snapshots.append(entry.name)
    for dirpath, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = [d for d in dirs if not _excluded(d, exclude)]
        for name in files:
            if counts["files"] >= MAX_FILES:
                truncated = True
                break
            path = Path(dirpath) / name
            try:
                stat = path.stat()
            except OSError:
                continue
            counts["files"] += 1
            bytes_total += stat.st_size
            latest = max(latest, stat.st_mtime)
            suffix = path.suffix.lower()
            if suffix == ".md":
                counts["md"] += 1
            elif suffix == ".py":
                counts["py"] += 1
            elif suffix in {".js", ".mjs", ".cjs"}:
                counts["js"] += 1
            elif suffix == ".parquet":
                counts["parquet"] += 1
            elif suffix in DB_SUFFIXES:
                counts["db"] += 1
                if len(db_files) < 20:
                    db_files.append({"path": str(path.relative_to(root)), "bytes": stat.st_size})
        if truncated:
            break
    counts["bytes"] = bytes_total
    counts["last_activity"] = _date(latest) if latest else ""
    counts["truncated"] = truncated
    counts["snapshots"] = sorted(snapshots)
    counts["db_files"] = db_files
    return counts


def _app_hint(readme: str) -> int | None:
    patterns = (
        r"localhost:(\d{2,5})", r"127\.0\.0\.1:(\d{2,5})",
        r"--port\s+(\d{2,5})",
    )
    for pattern in patterns:
        match = re.search(pattern, readme, re.I)
        if match:
            port = int(match.group(1))
            if 1 <= port <= 65535:
                return port
    return None


def _describe(root: Path, path: Path, names: list[str], evidence: list[str], score: int, exclude: Iterable[str]) -> dict[str, Any]:
    readme_text = ""
    readme_name = next((name for name in README_FILES if name in names), "")
    if readme_name:
        try:
            readme_text = (path / readme_name).read_text(encoding="utf-8", errors="replace")[:MAX_README]
        except OSError:
            pass
    heading, description = _readme(path, names)
    name = heading or path.name
    stats = _stats(path, exclude=exclude)
    kind = "unknown"
    if "database" in evidence:
        kind = "data_app"
    elif "strong-manifest" in evidence:
        kind = "software"
    elif stats["md"] >= 10 and stats["py"] >= 5:
        kind = "research"
    elif stats["md"] >= 10:
        kind = "book"
    return {
        "code": _slug(name),
        "name": name,
        "path": str(path),
        "relative_path": str(path.relative_to(root)),
        "description": description,
        "type": kind,
        "status": "candidate",
        "evidence": evidence,
        "score": score,
        "recommendation": "strong" if score >= 4 else "possible",
        "counts": stats,
        "app_port": _app_hint(readme_text),
        "source_state": "available",
    }


def scan(
    root: str | Path,
    *,
    depth: int = 3,
    min_score: int = 2,
    limit: int = 200,
    exclude: Iterable[str] = (),
) -> dict[str, Any]:
    root = Path(root).expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"project root not found: {root}")
    patterns = tuple(exclude)
    found: list[dict[str, Any]] = []
    visited = 0

    def walk(path: Path, level: int) -> None:
        nonlocal visited
        if len(found) >= limit or level > depth:
            return
        visited += 1
        evidence, names, score = _markers(path)
        if score >= min_score:
            found.append(_describe(root, path, names, evidence, score, patterns))
            return
        try:
            children = sorted(
                (entry for entry in os.scandir(path) if entry.is_dir(follow_symlinks=False)),
                key=lambda entry: entry.name.lower(),
            )
        except OSError:
            return
        for child in children:
            if _excluded(child.name, patterns):
                continue
            walk(Path(child.path), level + 1)

    walk(root, 0)
    return {
        "root": str(root),
        "depth": depth,
        "visited": visited,
        "count": len(found),
        "projects": found,
        "read_only": True,
    }
