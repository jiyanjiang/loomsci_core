"""Resolve the loomsci home and plan a legacy-home migration.

The single-machine profile uses one canonical home. It never guesses when both
the new and legacy homes exist: the caller must pass an explicit home or run a
migration.
"""

from __future__ import annotations

import os
import shutil
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


class HomeError(RuntimeError):
    """Base error for home resolution and migration."""


class HomeConflict(HomeError):
    """Both the new and legacy homes exist without an explicit choice."""


@dataclass(frozen=True)
class HomeResolution:
    path: Path
    source: str
    legacy: bool = False
    needs_migration: bool = False


@dataclass(frozen=True)
class Layout:
    root: Path
    data: Path
    db: Path
    blobs: Path
    agents: Path
    packs: Path
    logs: Path
    runtime: Path
    port_file: Path


@dataclass(frozen=True)
class MigrationItem:
    name: str
    source: Path
    destination: Path
    kind: str
    exists: bool
    files: int = 0
    bytes: int = 0
    note: str = ""


@dataclass(frozen=True)
class MigrationPlan:
    source: Path
    destination: Path
    items: tuple[MigrationItem, ...]
    counts: Mapping[str, int]
    warnings: tuple[str, ...] = ()


def default_home(home_dir: Path | None = None) -> Path:
    return Path(home_dir or Path.home()) / ".loomsci"


def legacy_home(home_dir: Path | None = None) -> Path:
    return Path(home_dir or Path.home()) / ".taa"


def _is_legacy(path: Path) -> bool:
    return path.name == ".taa"


def resolve_home(
    explicit: str | Path | None = None,
    env: Mapping[str, str] | None = None,
    home_dir: Path | None = None,
) -> HomeResolution:
    """Resolve the instance home without creating it.

    Priority: explicit > LOOMSCI_HOME > TAA_HOME > ~/.loomsci > ~/.taa.
    Both homes present without explicit/env is an error.
    """

    values = os.environ if env is None else env
    if explicit is not None and str(explicit).strip():
        path = Path(str(explicit)).expanduser()
        return HomeResolution(
            path=path,
            source="explicit",
            legacy=_is_legacy(path),
        )

    for key in ("LOOMSCI_HOME", "TAA_HOME"):
        raw = str(values.get(key) or "").strip()
        if raw:
            path = Path(raw).expanduser()
            return HomeResolution(
                path=path,
                source=key.lower(),
                legacy=_is_legacy(path) or key == "TAA_HOME",
            )

    new = default_home(home_dir)
    old = legacy_home(home_dir)
    new_exists, old_exists = new.exists(), old.exists()
    if new_exists and old_exists:
        raise HomeConflict(
            f"both {new} and {old} exist; pass --home or migrate explicitly"
        )
    if new_exists:
        return HomeResolution(path=new, source="default")
    if old_exists:
        return HomeResolution(
            path=old,
            source="legacy",
            legacy=True,
            needs_migration=True,
        )
    return HomeResolution(path=new, source="default")


def ensure_layout(root: str | Path) -> Layout:
    """Create the instance directories; never create user data files."""

    root = Path(root).expanduser()
    data = root / "data"
    layout = Layout(
        root=root,
        data=data,
        db=data / "data.db",
        blobs=data / "blobs",
        agents=root / "agents",
        packs=root / "packs",
        logs=root / "logs",
        runtime=root / "runtime",
        port_file=root / "runtime" / "port",
    )
    for path in (
        layout.root,
        layout.data,
        layout.blobs,
        layout.agents,
        layout.packs,
        layout.logs,
        layout.runtime,
    ):
        path.mkdir(parents=True, exist_ok=True)
        _chmod_private(path)
    return layout


def _chmod_private(path: Path) -> None:
    try:
        os.chmod(path, 0o700)
    except OSError:
        # Windows ACLs and some filesystems do not support POSIX modes.
        pass


def _sqlite_uri(path: Path) -> str:
    return f"{path.resolve().as_uri()}?mode=ro"


def _table_counts(db: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    if not db.is_file():
        return counts
    try:
        conn = sqlite3.connect(_sqlite_uri(db), uri=True)
    except sqlite3.Error:
        return counts
    try:
        for table in ("agents", "posts", "tasks"):
            try:
                counts[table] = int(
                    conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                )
            except sqlite3.Error:
                continue
    finally:
        conn.close()
    return counts


def _tree_stats(path: Path) -> tuple[int, int]:
    files = 0
    total = 0
    if not path.exists():
        return 0, 0
    for item in path.rglob("*"):
        if item.is_file():
            files += 1
            try:
                total += item.stat().st_size
            except OSError:
                pass
    return files, total


def migration_plan(source: str | Path, destination: str | Path) -> MigrationPlan:
    """Describe what would be copied; does not write anything."""

    source = Path(source).expanduser()
    destination = Path(destination).expanduser()
    if not source.is_dir():
        raise HomeError(f"source home not found: {source}")
    if source.resolve() == destination.resolve():
        raise HomeError("source and destination are the same")
    if destination.exists() and any(destination.iterdir()):
        raise HomeError(f"destination is not empty: {destination}")

    items: list[MigrationItem] = []
    warnings: list[str] = []

    db = source / "data.db"
    if db.is_file():
        items.append(MigrationItem(
            name="data.db",
            source=db,
            destination=destination / "data" / "data.db",
            kind="sqlite",
            exists=True,
            files=1,
            bytes=db.stat().st_size,
        ))

    agents = source / "agents"
    if agents.is_dir():
        files, size = _tree_stats(agents)
        items.append(MigrationItem(
            name="agents",
            source=agents,
            destination=destination / "agents",
            kind="tree",
            exists=True,
            files=files,
            bytes=size,
        ))

    for name in ("config.toml", "config.yaml"):
        cfg = source / name
        if cfg.is_file():
            items.append(MigrationItem(
                name=name,
                source=cfg,
                destination=destination / name,
                kind="file",
                exists=True,
                files=1,
                bytes=cfg.stat().st_size,
            ))

    for name in ("static/uploads", "events.db", "bootstrap", "rooms"):
        if (source / name).exists():
            warnings.append(f"not migrated automatically: {name}")

    counts = _table_counts(db)
    return MigrationPlan(
        source=source,
        destination=destination,
        items=tuple(items),
        counts=counts,
        warnings=tuple(warnings),
    )


def _copy_sqlite(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise HomeError(f"destination database already exists: {destination}")
    src = sqlite3.connect(_sqlite_uri(source), uri=True)
    dst = sqlite3.connect(str(destination))
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()


def apply_migration(plan: MigrationPlan, *, dry_run: bool = True) -> dict:
    """Copy the planned items; source is never modified or deleted."""

    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "source": str(plan.source),
            "destination": str(plan.destination),
            "items": [item.name for item in plan.items],
            "counts": dict(plan.counts),
            "warnings": list(plan.warnings),
        }

    destination = plan.destination
    destination.mkdir(parents=True, exist_ok=True)
    for item in plan.items:
        if item.kind == "sqlite":
            _copy_sqlite(item.source, item.destination)
        elif item.kind == "tree":
            # The destination root may already contain empty layout directories.
            shutil.copytree(item.source, item.destination, dirs_exist_ok=True)
        elif item.kind == "file":
            item.destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item.source, item.destination)
        else:
            raise HomeError(f"unknown migration item: {item.name}")

    after = _table_counts(destination / "data" / "data.db")
    for table, expected in plan.counts.items():
        actual = after.get(table)
        if actual != expected:
            raise HomeError(
                f"migration count mismatch for {table}: {actual} != {expected}"
            )
    return {
        "ok": True,
        "dry_run": False,
        "source": str(plan.source),
        "destination": str(plan.destination),
        "items": [item.name for item in plan.items],
        "counts": dict(plan.counts),
        "warnings": list(plan.warnings),
    }
