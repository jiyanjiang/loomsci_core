"""Data-only backup/restore for the Core v0 prototype."""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import shutil
import sqlite3
import time
from pathlib import Path


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _files(root: Path) -> list[dict]:
    out = []
    for path in sorted(root.rglob("*")):
        if path.is_file():
            out.append({
                "path": path.relative_to(root).as_posix(),
                "sha256": _hash(path),
                "bytes": path.stat().st_size,
            })
    return out


def _copy_tree(source: Path, target: Path) -> None:
    if not source.is_dir():
        return
    target.mkdir(parents=True, exist_ok=True)
    for path in source.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(source)
        if "venv" in rel.parts or "__pycache__" in rel.parts:
            continue
        destination = target / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)


def create(home: Path, out: Path | None = None) -> Path:
    home = home.expanduser()
    source_db = home / "data" / "core.db"
    if not source_db.is_file():
        raise ValueError("core_db_missing")
    if out is None:
        stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        out = home / "backups" / ("backup-" + stamp)
    if out.exists():
        raise ValueError("backup_exists")
    tmp = out.with_name(out.name + ".tmp-" + str(os.getpid()))
    if tmp.exists():
        shutil.rmtree(tmp)
    try:
        (tmp / "data").mkdir(parents=True)
        src = sqlite3.connect(str(source_db))
        dst = sqlite3.connect(str(tmp / "data" / "core.db"))
        with dst:
            src.backup(dst)
        src.close(); dst.close()
        _copy_tree(home / "data" / "blobs", tmp / "data" / "blobs")
        if (home / "apps").is_dir():
            for app in sorted((home / "apps").iterdir()):
                if app.is_dir():
                    _copy_tree(app / "data", tmp / "apps" / app.name / "data")
            installed = home / "apps" / "installed.json"
            if installed.is_file():
                (tmp / "apps").mkdir(parents=True, exist_ok=True)
                shutil.copy2(installed, tmp / "apps" / "installed.json")
        manifest = {
            "format": "loomsci-backup/1",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "core_version": "core-v0",
            "core_api": "core/1",
            "files": _files(tmp),
        }
        (tmp / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.rename(out)
        return out
    except Exception:
        if tmp.exists():
            shutil.rmtree(tmp)
        raise


def verify(backup: Path) -> dict:
    manifest_path = backup / "manifest.json"
    if not manifest_path.is_file():
        raise ValueError("manifest_missing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("format") != "loomsci-backup/1":
        raise ValueError("bad_format")
    for item in manifest.get("files") or []:
        path = backup / item["path"]
        if not path.is_file() or path.stat().st_size != item["bytes"] or _hash(path) != item["sha256"]:
            raise ValueError("hash_mismatch:" + item["path"])
    return manifest


def restore(backup: Path, target: Path) -> dict:
    manifest = verify(backup)
    target = target.expanduser()
    if target.exists():
        raise ValueError("target_exists")
    tmp = target.with_name(target.name + ".tmp-" + str(os.getpid()))
    if tmp.exists():
        shutil.rmtree(tmp)
    try:
        tmp.mkdir(parents=True)
        shutil.copytree(backup / "data", tmp / "data", dirs_exist_ok=True)
        if (backup / "apps").is_dir():
            shutil.copytree(backup / "apps", tmp / "apps", dirs_exist_ok=True)
        token = tmp / "local.token"
        token.write_text(secrets.token_hex(32) + "\n", encoding="utf-8")
        try:
            token.chmod(0o600)
        except OSError:
            pass
        tmp.rename(target)
        return {"restored": True, "target": str(target), "files": len(manifest.get("files") or [])}
    except Exception:
        if tmp.exists():
            shutil.rmtree(tmp)
        raise


def list_backups(home: Path) -> list[dict]:
    base = home.expanduser() / "backups"
    if not base.is_dir():
        return []
    out = []
    for path in sorted(base.iterdir()):
        if path.is_dir() and (path / "manifest.json").is_file():
            out.append({"name": path.name, "path": str(path)})
    return out
