"""Local add-on catalog and lifecycle.

This is intentionally not a marketplace: it reads bundled manifests, records
installed versions under ``packs/``, and copies/removes add-on directories.
It never imports add-on code.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parent.parent
BUNDLED = ROOT / "addons"
STATE_SCHEMA = 2
CONTRACT = {
    "api": "core/1",
    "required": ["name", "version", "api", "package", "entry", "port", "health"],
    "defaults": {"package": "name with '-' replaced by '_'", "entry": "server", "port": 0, "health": "/"},
    "optional": ["requires", "routes", "storage", "jobs", "nav", "preserve"],
    "rules": [
        "Core never imports add-on code.",
        "Add-ons use public Core /v1 APIs; no core.storage imports.",
        "Each add-on has an isolated package, storage namespace, port, and health path.",
        "Manifest api must equal core/1.",
        "Installed data lives in packs/<package>/data/ and survives update.",
    ],
}
PROFILES = {
    "minimal": [],
    "personal": ["ui-shell", "notify"],
    "maker": ["ui-shell", "media", "research"],
    "team": ["ui-shell", "collab", "notify"],
    "full": ["ui-shell", "collab", "notify", "media", "research"],
}


class AddonError(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


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
    name = str(data.get("name") or "").strip()
    if not name:
        raise AddonError(f"name missing: {source}")
    package = str(data.get("package") or name.replace("-", "_")).strip()
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", package):
        raise AddonError(f"invalid package name for {name}: {package}")
    entry = str(data.get("entry") or "server").strip()
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", entry):
        raise AddonError(f"invalid entry for {name}: {entry}")
    port = data.get("port", 0)
    if not isinstance(port, int) or not 0 <= port <= 65535:
        raise AddonError(f"invalid port for {name}: {port!r}")
    health = str(data.get("health") or "/").strip()
    if not health.startswith("/"):
        raise AddonError(f"invalid health path for {name}: {health}")
    requires = data.get("requires", [])
    if not isinstance(requires, list) or not all(isinstance(item, str) for item in requires):
        raise AddonError(f"invalid requires for {name}")
    data["name"] = name
    data["package"] = package
    data["entry"] = entry
    data["port"] = port
    data["health"] = health
    data["requires"] = requires
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


def _read_state(home: Path) -> dict[str, dict[str, Any]]:
    path = _state_path(home)
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    raw = data.get("addons", {}) if isinstance(data, dict) else data
    if isinstance(raw, list):
        return {str(name): {} for name in raw}
    if isinstance(raw, dict):
        return {str(name): value if isinstance(value, dict) else {} for name, value in raw.items()}
    return {}


def _write_state(home: Path, records: dict[str, dict[str, Any]]) -> None:
    path = _state_path(home)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"schema": STATE_SCHEMA, "addons": dict(sorted(records.items()))}
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def installed(home: Path) -> list[str]:
    return sorted(_read_state(home))


def record(home: Path, name: str) -> dict[str, Any]:
    return dict(_read_state(home).get(name, {}))


def target(home: Path, name: str, data: dict[str, Any] | None = None) -> Path:
    package = str((data or record(home, name)).get("package") or "").strip()
    if package and not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", package):
        raise AddonError(f"invalid installed package for {name}: {package}")
    if not package:
        try:
            package = str(read_manifest(_source_for(name))["package"])
        except AddonError:
            package = name.replace("-", "_")
    return home / "packs" / package


def _tree_hash(source: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(source.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(source)
        if "data" in rel.parts or "__pycache__" in rel.parts or path.suffix == ".pyc":
            continue
        digest.update(rel.as_posix().encode("utf-8") + b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _version_key(value: str) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", str(value)))


def _parse_requirement(value: str) -> tuple[str | None, str | None]:
    token = value.strip()
    if token.startswith("core/"):
        return None, None
    match = re.fullmatch(r"([A-Za-z0-9_-]+)(?:>=([0-9][0-9A-Za-z.\-]*))?", token)
    if not match:
        raise AddonError(f"invalid add-on requirement: {value}")
    return match.group(1), match.group(2)


def _check_requires(manifest: dict[str, Any], records: dict[str, dict[str, Any]]) -> None:
    for value in manifest.get("requires", []):
        name, minimum = _parse_requirement(str(value))
        if name is None:
            continue
        if name not in records:
            raise AddonError(f"{manifest['name']} requires add-on {name}")
        if minimum is not None:
            current = str(records[name].get("version") or "0")
            if _version_key(current) < _version_key(minimum):
                raise AddonError(
                    f"{manifest['name']} requires {name}>={minimum}, installed {current}"
                )


def _copy_code(source: Path, destination: Path) -> None:
    """Replace code, keep an existing ``data/`` directory."""
    data = destination / "data"
    backup = destination.parent / f".{destination.name}.data.tmp"
    if data.exists():
        if backup.exists():
            shutil.rmtree(backup)
        shutil.move(str(data), str(backup))
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(
        source,
        destination,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
    )
    if backup.exists():
        shutil.move(str(backup), str(destination / "data"))


def _migrate_legacy_target(home: Path, name: str, destination: Path) -> None:
    legacy = home / "packs" / name
    if legacy == destination or not legacy.is_dir():
        return
    legacy_data = legacy / "data"
    if legacy_data.exists():
        destination.mkdir(parents=True, exist_ok=True)
        shutil.copytree(legacy_data, destination / "data", dirs_exist_ok=True)
    shutil.rmtree(legacy)


def install(home: Path, name: str) -> dict[str, Any]:
    source = _source_for(name)
    manifest = read_manifest(source)
    records = _read_state(home)
    _check_requires(manifest, records)
    destination = home / "packs" / manifest["package"]
    destination.parent.mkdir(parents=True, exist_ok=True)
    (destination.parent / "__init__.py").touch(exist_ok=True)
    _copy_code(source, destination)
    _migrate_legacy_target(home, name, destination)
    records[name] = {
        "version": str(manifest.get("version") or ""),
        "package": manifest["package"],
        "sha256": _tree_hash(source),
        "installed_at": _now(),
    }
    _write_state(home, records)
    return {
        "name": name,
        "version": manifest.get("version"),
        "package": manifest["package"],
        "path": str(destination),
        "sha256": records[name]["sha256"],
    }


def update(home: Path, name: str) -> dict[str, Any]:
    records = _read_state(home)
    if name not in records:
        raise AddonError(f"addon not installed: {name}")
    source = _source_for(name)
    manifest = read_manifest(source)
    _check_requires(manifest, records)
    destination = target(home, name, records[name])
    _copy_code(source, destination)
    _migrate_legacy_target(home, name, destination)
    previous = str(records[name].get("version") or "")
    records[name].update({
        "version": str(manifest.get("version") or ""),
        "package": manifest["package"],
        "sha256": _tree_hash(source),
        "installed_at": _now(),
    })
    _write_state(home, records)
    return {
        "name": name,
        "previous_version": previous,
        "version": manifest.get("version"),
        "package": manifest["package"],
        "path": str(destination),
        "updated": previous != str(manifest.get("version") or ""),
    }


def update_all(home: Path) -> list[dict[str, Any]]:
    return [update(home, name) for name in installed(home)]


def verify(home: Path) -> dict[str, Any]:
    records = _read_state(home)
    results = []
    for name in sorted(records):
        entry = records[name]
        destination = target(home, name, entry)
        source = None
        try:
            source = _source_for(name)
        except AddonError:
            pass
        manifest = read_manifest(source) if source else None
        checks = {
            "name": name,
            "installed": destination.is_dir(),
            "version": entry.get("version"),
            "bundled_version": manifest.get("version") if manifest else None,
            "hash_match": bool(source) and entry.get("sha256") == _tree_hash(source),
            "update_available": bool(manifest) and entry.get("version") != manifest.get("version"),
        }
        checks["ok"] = checks["installed"] and checks["hash_match"]
        results.append(checks)
    return {"ok": all(item["ok"] for item in results), "addons": results}


def remove(home: Path, name: str) -> dict[str, Any]:
    records = _read_state(home)
    data = records.get(name)
    destination = target(home, name, data)
    legacy = home / "packs" / name
    if not data and legacy.is_dir():
        destination = legacy
    if destination.exists():
        data = destination / "data"
        backup = home / "packs" / f".{destination.name}.data"
        if data.exists():
            if backup.exists():
                shutil.rmtree(backup)
            shutil.move(str(data), str(backup))
        shutil.rmtree(destination)
        if backup.exists():
            destination.mkdir(parents=True, exist_ok=True)
            shutil.move(str(backup), str(destination / "data"))
    records.pop(name, None)
    _write_state(home, records)
    return {"name": name, "removed": True}


def install_profile(home: Path, profile: str) -> list[dict[str, Any]]:
    names = PROFILES.get(profile)
    if names is None:
        raise AddonError(f"unknown profile: {profile}")
    return [install(home, name) for name in names]
