#!/usr/bin/env python3
"""Minimal data-only backup/restore prototype for Core + Apps.

Not product code. Validates the data-layering and backup semantics:
- core DB + blobs + app data + installed.json
- excludes token/logs/venv/code
- manifest hashes
- verify, restore, failure safety
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


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _files(root: Path) -> list[dict]:
    items = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        items.append({
            "path": path.relative_to(root).as_posix(),
            "sha256": _hash_file(path),
            "bytes": path.stat().st_size,
        })
    return items


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


def create(home: Path, out: Path) -> dict:
    if out.exists():
        raise SystemExit(f"output already exists: {out}")
    home = home.expanduser()
    if not (home / "data" / "core.db").is_file():
        raise SystemExit(f"core DB missing: {home / 'data' / 'core.db'}")
    tmp = out.with_name(out.name + ".tmp-" + str(os.getpid()))
    if tmp.exists():
        shutil.rmtree(tmp)
    try:
        (tmp / "data").mkdir(parents=True)
        source = sqlite3.connect(str(home / "data" / "core.db"))
        target = sqlite3.connect(str(tmp / "data" / "core.db"))
        with target:
            source.backup(target)
        source.close()
        target.close()
        _copy_tree(home / "data" / "blobs", tmp / "data" / "blobs")
        if (home / "apps").is_dir():
            for app in sorted((home / "apps").iterdir()):
                if not app.is_dir():
                    continue
                _copy_tree(app / "data", tmp / "apps" / app.name / "data")
            installed = home / "apps" / "installed.json"
            if installed.is_file():
                (tmp / "apps").mkdir(parents=True, exist_ok=True)
                shutil.copy2(installed, tmp / "apps" / "installed.json")
        manifest = {
            "format": "loomsci-backup/1",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "core_version": "prototype",
            "core_api": "core/1",
            "apps": [],
            "files": _files(tmp),
        }
        (tmp / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        tmp.rename(out)
        return manifest
    except Exception:
        if tmp.exists():
            shutil.rmtree(tmp)
        raise


def verify(backup: Path) -> dict:
    manifest_path = backup / "manifest.json"
    if not manifest_path.is_file():
        raise SystemExit("manifest missing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("format") != "loomsci-backup/1":
        raise SystemExit("bad backup format")
    for item in manifest.get("files") or []:
        path = backup / item["path"]
        if not path.is_file():
            raise SystemExit(f"missing file: {item['path']}")
        if path.stat().st_size != item["bytes"]:
            raise SystemExit(f"size mismatch: {item['path']}")
        if _hash_file(path) != item["sha256"]:
            raise SystemExit(f"hash mismatch: {item['path']}")
    return manifest


def restore(backup: Path, home: Path, force: bool = False) -> dict:
    manifest = verify(backup)
    home = home.expanduser()
    if home.exists() and any(home.iterdir()) and not force:
        raise SystemExit(f"target not empty; use --force: {home}")
    previous = None
    if home.exists():
        previous = home.with_name(home.name + ".pre-restore-" + str(int(time.time())))
        home.rename(previous)
    try:
        home.mkdir(parents=True)
        shutil.copytree(backup / "data", home / "data", dirs_exist_ok=True)
        if (backup / "apps").is_dir():
            shutil.copytree(backup / "apps", home / "apps", dirs_exist_ok=True)
        token = home / "local.token"
        token.write_text(secrets.token_hex(32) + "\n", encoding="utf-8")
        try:
            token.chmod(0o600)
        except OSError:
            pass
        return {"restored": True, "files": len(manifest.get("files") or []), "home": str(home)}
    except Exception:
        if home.exists():
            shutil.rmtree(home)
        if previous and previous.exists():
            previous.rename(home)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    create_cmd = sub.add_parser("create")
    create_cmd.add_argument("--home", required=True)
    create_cmd.add_argument("--out", required=True)
    verify_cmd = sub.add_parser("verify")
    verify_cmd.add_argument("--backup", required=True)
    restore_cmd = sub.add_parser("restore")
    restore_cmd.add_argument("--backup", required=True)
    restore_cmd.add_argument("--home", required=True)
    restore_cmd.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if args.command == "create":
        result = create(Path(args.home), Path(args.out))
    elif args.command == "verify":
        result = verify(Path(args.backup))
    else:
        result = restore(Path(args.backup), Path(args.home), args.force)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
