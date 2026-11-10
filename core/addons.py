"""Minimal local add-on host.

This is intentionally not a marketplace: it reads bundled add-on manifests,
records installed names in the home, and copies/removes add-on directories.
It never imports add-on code.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
BUNDLED = ROOT / "addons"
PROFILES = {
    "minimal": [],
    "personal": ["ui-shell", "notify"],
}


class AddonError(RuntimeError):
    pass


def _manifest_path(source: Path) -> Path:
    return source / "manifest.json"


def read_manifest(source: Path) -> dict[str, Any]:
    path = _manifest_path(source)
    if not path.is_file():
        raise AddonError(f"manifest missing: {source}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise AddonError(f"invalid manifest: {source}") from exc
    if data.get("api") != "core/1":
        raise AddonError(f"unsupported api for {source.name}: {data.get('api')}")
    if not str(data.get("name") or "").strip():
        raise AddonError(f"name missing: {source}")
    return data


def _sources() -> list[tuple[str, Path, dict[str, Any]]]:
    items = []
    if not BUNDLED.is_dir():
        return items
    for source in sorted(BUNDLED.iterdir()):
        if not source.is_dir() or source.name.startswith("_"):
            continue
        try:
            manifest = read_manifest(source)
        except AddonError:
            continue
        items.append((str(manifest["name"]), source, manifest))
    return items


def available() -> list[dict[str, Any]]:
    return [manifest for _name, _source, manifest in _sources()]


def _source_for(name: str) -> Path:
    for item_name, source, _manifest in _sources():
        if item_name == name:
            return source
    raise AddonError(f"addon not found: {name}")


def _state_path(home: Path) -> Path:
    return home / "packs" / "installed.json"


def installed(home: Path) -> list[str]:
    path = _state_path(home)
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return sorted(str(item) for item in data.get("addons", []))
    except (OSError, ValueError):
        return []


def _write_state(home: Path, names: list[str]) -> None:
    path = _state_path(home)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"addons": sorted(set(names))}, indent=2) + "\n",
        encoding="utf-8",
    )


def install(home: Path, name: str) -> dict[str, Any]:
    source = _source_for(name)
    manifest = read_manifest(source)
    target = home / "packs" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    # Never delete add-on data on reinstall; overwrite code/manifest only.
    shutil.copytree(source, target, dirs_exist_ok=True)
    names = installed(home)
    if name not in names:
        names.append(name)
    _write_state(home, names)
    return {"name": name, "version": manifest.get("version"), "path": str(target)}


def remove(home: Path, name: str) -> dict[str, Any]:
    target = home / "packs" / name
    if target.exists():
        data = target / "data"
        backup = home / "packs" / f".{name}.data"
        if data.exists():
            if backup.exists():
                shutil.rmtree(backup)
            shutil.move(str(data), str(backup))
        shutil.rmtree(target)
        if backup.exists():
            target.mkdir(parents=True, exist_ok=True)
            shutil.move(str(backup), str(target / "data"))
    names = [item for item in installed(home) if item != name]
    _write_state(home, names)
    return {"name": name, "removed": True}


def install_profile(home: Path, profile: str) -> list[dict[str, Any]]:
    names = PROFILES.get(profile)
    if names is None:
        raise AddonError(f"unknown profile: {profile}")
    return [install(home, name) for name in names]
