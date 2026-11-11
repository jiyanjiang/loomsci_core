"""Workspace migration into an installed, empty Loomsci home."""

from __future__ import annotations

import shutil
import sqlite3
import zipfile
from pathlib import Path
from typing import Any

from core import backup


class MigrationError(RuntimeError):
    pass


def _db_state(db: Path) -> tuple[str, dict[str, int]]:
    if not db.is_file():
        return "empty", {}
    conn = None
    try:
        conn = sqlite3.connect(f"file:{db.resolve().as_posix()}?mode=ro", uri=True)
        counts = {}
        for table in ("posts", "tasks", "facts", "attachments"):
            try:
                counts[table] = int(conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0])
            except sqlite3.Error:
                counts[table] = 0
        return ("used" if any(counts.values()) else "empty"), counts
    except sqlite3.Error:
        return "unknown", {}
    finally:
        if conn is not None:
            conn.close()


def state(home: str | Path) -> dict[str, Any]:
    home = Path(home).expanduser()
    state_value, counts = _db_state(home / "data" / "data.db")
    packs_data = []
    packs = home / "packs"
    if packs.is_dir():
        for pack in packs.iterdir():
            data = pack / "data"
            if data.is_dir() and any(path.is_file() for path in data.rglob("*")):
                packs_data.append(pack.name)
    if state_value == "empty" and packs_data:
        state_value = "unknown"
    return {
        "home": str(home),
        "state": state_value,
        "counts": counts,
        "packs_with_data": sorted(packs_data),
        "config": (home / "config.yaml").is_file(),
    }


def _bundle_agents(bundle: str | Path) -> set[str]:
    try:
        with zipfile.ZipFile(bundle) as zf:
            names = zf.namelist()
    except (OSError, zipfile.BadZipFile):
        return set()
    handles = set()
    for name in names:
        parts = Path(name).parts
        if len(parts) >= 2 and parts[0] == "agents":
            handles.add(parts[1])
    return handles


def _preserve_default_agents(home: Path, source_agents: set[str]) -> list[str]:
    agents = home / "agents"
    if not agents.is_dir() or not source_agents:
        return []
    preserved = []
    target = home / "runtime" / "pre-import-agents"
    for entry in agents.iterdir():
        if not entry.is_dir() or entry.name in source_agents:
            continue
        target.mkdir(parents=True, exist_ok=True)
        destination = target / entry.name
        if destination.exists():
            shutil.rmtree(destination)
        shutil.move(str(entry), str(destination))
        preserved.append(entry.name)
    return preserved


def import_bundle(bundle: str | Path, home: str | Path, *, apply: bool = False) -> dict[str, Any]:
    target = Path(home).expanduser()
    current = state(target)
    if current["state"] == "used":
        raise MigrationError("target already has user data; migration refuses to overwrite")
    if current["state"] == "unknown":
        raise MigrationError("target state is unknown; inspect and resolve it before migration")
    verified = backup.verify_bundle(bundle)
    if not verified["ok"]:
        raise MigrationError("source bundle verification failed")
    if not apply:
        return {
            "ok": True,
            "dry_run": True,
            "source": verified,
            "target": current,
            "would_restore": True,
        }
    preserved_agents = _preserve_default_agents(target, _bundle_agents(bundle))
    restored = backup.restore_bundle(bundle, target, apply=True, allow_existing=True)
    return {
        "ok": True,
        "dry_run": False,
        "source": verified,
        "target": current,
        "restored": restored,
        "preserved_agents": preserved_agents,
        "state_after": state(target),
    }
