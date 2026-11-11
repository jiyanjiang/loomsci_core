"""Read-mostly storage health, duplicate detection, and safe compaction."""

from __future__ import annotations

import os
import sqlite3
import time
from collections import defaultdict
from pathlib import Path
from typing import Any


def _db(home: Path) -> Path:
    return home / "data" / "data.db"


def _blob_dir(home: Path) -> Path:
    return home / "data" / "blobs"


def _size(path: Path) -> int:
    try:
        return path.stat().st_size if path.is_file() else 0
    except OSError:
        return 0


def _tree_size(path: Path) -> int:
    if not path.is_dir():
        return 0
    return sum(_size(item) for item in path.rglob("*") if item.is_file())


def _rows(home: Path) -> list[dict[str, Any]]:
    db = _db(home)
    if not db.is_file():
        return []
    conn = None
    try:
        conn = sqlite3.connect(f"file:{db.resolve().as_posix()}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        return [dict(row) for row in conn.execute("SELECT * FROM attachments ORDER BY id").fetchall()]
    except sqlite3.Error:
        return []
    finally:
        if conn is not None:
            conn.close()


def _groups(rows: list[dict[str, Any]], blobs: Path) -> list[dict[str, Any]]:
    by_hash: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        digest = str(row.get("sha256") or "")
        if digest:
            by_hash[digest].append(row)
    result = []
    for digest, items in by_hash.items():
        if len(items) < 2:
            continue
        size = max(int(item.get("bytes") or 0) for item in items)
        paths = [blobs / str(item.get("id")) for item in items if item.get("id")]
        inodes = set()
        for path in paths:
            try:
                stat = path.stat()
                inodes.add((stat.st_dev, stat.st_ino))
            except OSError:
                pass
        reclaimable = size * max(0, len(inodes) - 1)
        result.append({
            "sha256": digest,
            "count": len(items),
            "bytes": size * len(items),
            "reclaimable_bytes": reclaimable,
            "attachments": [
                {"id": item.get("id"), "filename": item.get("filename"), "post_id": item.get("post_id")}
                for item in items
            ],
        })
    result.sort(key=lambda item: item["reclaimable_bytes"], reverse=True)
    return result


def report(home: str | Path) -> dict[str, Any]:
    home = Path(home).expanduser()
    rows = _rows(home)
    blobs = _blob_dir(home)
    referenced = {str(row["id"]): row for row in rows if row.get("id")}
    files = {path.name: path for path in blobs.iterdir() if path.is_file()} if blobs.is_dir() else {}
    groups = _groups(rows, blobs)
    duplicates = sum(item["reclaimable_bytes"] for item in groups)
    orphans = [
        {"name": name, "bytes": _size(path), "mtime": path.stat().st_mtime}
        for name, path in files.items() if name not in referenced
    ]
    missing = [item for item in rows if str(item.get("id")) not in files]
    db = _db(home)
    db_bytes = sum(_size(db.with_name(db.name + suffix)) for suffix in ("", "-wal", "-shm"))
    log_bytes = _tree_size(home / "logs")
    cache_bytes = sum(
        _tree_size(home / "packs" / name / "data" / part)
        for name in ("media",)
        for part in ("thumbs", "ocr")
    )
    attachment_bytes = sum(int(row.get("bytes") or 0) for row in rows)
    orphan_bytes = sum(item["bytes"] for item in orphans)
    largest = sorted(
        ({"id": row.get("id"), "filename": row.get("filename"), "bytes": int(row.get("bytes") or 0)} for row in rows),
        key=lambda item: item["bytes"],
        reverse=True,
    )[:10]
    return {
        "ok": True,
        "home": str(home),
        "db_bytes": db_bytes,
        "blob_bytes": sum(_size(path) for path in files.values()),
        "blob_disk_bytes": sum(
            stat.st_size for stat in {
                (path.stat().st_dev, path.stat().st_ino): path.stat()
                for path in files.values()
                if path.exists()
            }.values()
        ),
        "attachments": {
            "count": len(rows),
            "bytes": attachment_bytes,
            "unique_hashes": len({row.get("sha256") for row in rows if row.get("sha256")}),
            "largest": largest,
        },
        "duplicates": {
            "groups": groups,
            "groups_count": len(groups),
            "reclaimable_bytes": duplicates,
        },
        "orphans": {
            "count": len(orphans),
            "bytes": orphan_bytes,
            "files": sorted(orphans, key=lambda item: item["bytes"], reverse=True)[:50],
        },
        "missing_blobs": {
            "count": len(missing),
            "attachments": [{"id": item.get("id"), "filename": item.get("filename")} for item in missing[:50]],
        },
        "logs_bytes": log_bytes,
        "derived_cache_bytes": cache_bytes,
        "reclaimable_bytes": duplicates + orphan_bytes,
    }


def duplicates(home: str | Path) -> dict[str, Any]:
    result = report(home)
    return {
        "ok": True,
        "home": result["home"],
        "groups": result["duplicates"]["groups"],
        "groups_count": result["duplicates"]["groups_count"],
        "reclaimable_bytes": result["duplicates"]["reclaimable_bytes"],
    }


def dedupe(home: str | Path, *, apply: bool = False) -> dict[str, Any]:
    home = Path(home).expanduser()
    report_data = duplicates(home)
    blobs = _blob_dir(home)
    replaced = 0
    failed = []
    reclaimed = 0
    for group in report_data["groups"]:
        paths = [blobs / str(item["id"]) for item in group["attachments"] if item.get("id")]
        paths = [path for path in paths if path.is_file()]
        if len(paths) < 2:
            continue
        canonical = paths[0]
        for target in paths[1:]:
            try:
                if os.path.samefile(canonical, target):
                    continue
            except OSError:
                pass
            size = _size(target)
            if not apply:
                replaced += 1
                reclaimed += size
                continue
            temp = target.with_name(target.name + ".dedupe.tmp")
            try:
                temp.unlink(missing_ok=True)
                os.link(canonical, temp)
                os.replace(temp, target)
                replaced += 1
                reclaimed += size
            except OSError as exc:
                temp.unlink(missing_ok=True)
                failed.append({"path": str(target), "error": str(exc)})
    return {
        "ok": True,
        "home": str(home),
        "apply": apply,
        "groups": report_data["groups_count"],
        "replaced": replaced,
        "reclaimable_bytes": reclaimed,
        "failed": failed,
    }


def prune(home: str | Path, *, apply: bool = False, older_than: int = 3600) -> dict[str, Any]:
    home = Path(home).expanduser()
    rows = {str(row["id"]) for row in _rows(home)}
    now = time.time()
    candidates = []
    blobs = _blob_dir(home)
    if blobs.is_dir():
        for item in blobs.iterdir():
            if not item.is_file() or item.name in rows:
                continue
            try:
                age = now - item.stat().st_mtime
            except OSError:
                continue
            if age >= older_than:
                candidates.append({"name": item.name, "bytes": _size(item)})
    removed = 0
    if apply:
        for item in candidates:
            try:
                (blobs / item["name"]).unlink()
                removed += 1
            except OSError:
                pass
    return {
        "ok": True,
        "home": str(home),
        "apply": apply,
        "older_than": older_than,
        "candidates": candidates,
        "bytes": sum(item["bytes"] for item in candidates),
        "removed": removed,
    }


def compact(home: str | Path, *, apply: bool = False) -> dict[str, Any]:
    home = Path(home).expanduser()
    db = _db(home)
    before = sum(_size(db.with_name(db.name + suffix)) for suffix in ("", "-wal", "-shm"))
    if not apply:
        return {"ok": True, "home": str(home), "apply": False, "before_bytes": before}
    conn = None
    try:
        conn = sqlite3.connect(db)
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conn.execute("VACUUM")
        conn.commit()
    except sqlite3.Error as exc:
        return {"ok": False, "home": str(home), "error": str(exc), "before_bytes": before}
    finally:
        if conn is not None:
            conn.close()
    after = sum(_size(db.with_name(db.name + suffix)) for suffix in ("", "-wal", "-shm"))
    return {"ok": True, "home": str(home), "apply": True, "before_bytes": before, "after_bytes": after, "reclaimed_bytes": max(0, before - after)}
