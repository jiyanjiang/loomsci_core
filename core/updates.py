"""Update metadata, download, and verification.

Installing is handled by the CLI/updater so the running Core can be stopped
before its code directory is replaced.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

DEFAULT_URL = "https://raw.githubusercontent.com/jiyanjiang/loomsci_core/main/releases/latest.json"
MAX_BYTES = 200 * 1024 * 1024


class UpdateError(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def version_key(value: str) -> tuple:
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z]+)\.?(\d+)?)?$", str(value).strip())
    if not match:
        return (0, 0, 0, 0, "", 0)
    major, minor, patch, label, number = match.groups()
    return (
        int(major), int(minor), int(patch),
        1 if not label else 0,
        (label or "").lower(),
        int(number or 0),
    )


def current_version(home: str | Path | None = None) -> str:
    if home:
        path = Path(home).expanduser() / "core" / "VERSION"
    else:
        path = Path(__file__).resolve().parents[1] / "VERSION"
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return "0.0.0"


def latest_url() -> str:
    env = os.environ.get("LOOMSCI_UPDATE_URL")
    return env or DEFAULT_URL


def _state_path(home: Path) -> Path:
    return home / "runtime" / "update.json"


def read_state(home: str | Path) -> dict[str, Any]:
    path = _state_path(Path(home).expanduser())
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    return data if isinstance(data, dict) else {}


def _write_state(home: Path, data: dict[str, Any]) -> None:
    path = _state_path(home)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def check(home: str | Path, *, timeout: int = 15) -> dict[str, Any]:
    home = Path(home).expanduser()
    request = urllib.request.Request(latest_url(), headers={"User-Agent": "loomsci-updater"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError, urllib.error.URLError) as exc:
        state = {**read_state(home), "checked_at": _now(), "error": type(exc).__name__}
        _write_state(home, state)
        raise UpdateError(f"update check failed: {type(exc).__name__}") from None
    if not isinstance(data, dict) or not data.get("version") or not data.get("url"):
        raise UpdateError("invalid update manifest")
    current = current_version(home)
    latest_version = str(data.get("version") or "")
    available = version_key(latest_version) > version_key(current)
    state = {
        **read_state(home),
        "checked_at": _now(),
        "current": current,
        "latest": data,
        "available": available,
        "error": None,
    }
    _write_state(home, state)
    return {"ok": True, "current": current, "available": available, "latest": data}


def download(home: str | Path, *, timeout: int = 60) -> dict[str, Any]:
    home = Path(home).expanduser()
    state = read_state(home)
    latest = state.get("latest")
    if not isinstance(latest, dict) or not latest.get("url"):
        raise UpdateError("check for updates first")
    package_url = urljoin(latest_url(), str(latest["url"]))
    expected = str(latest.get("sha256") or "").lower()
    folder = home / "updates"
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / Path(str(latest.get("url"))).name
    part = target.with_suffix(target.suffix + ".part")
    digest = hashlib.sha256()
    total = 0
    try:
        with urllib.request.urlopen(package_url, timeout=timeout) as response, part.open("wb") as fh:
            for chunk in iter(lambda: response.read(1024 * 1024), b""):
                total += len(chunk)
                if total > MAX_BYTES:
                    raise UpdateError("update package too large")
                digest.update(chunk)
                fh.write(chunk)
        actual = digest.hexdigest()
        if expected and actual != expected:
            raise UpdateError("SHA-256 mismatch")
        if latest.get("bytes") and int(latest["bytes"]) != total:
            raise UpdateError("size mismatch")
        os.replace(part, target)
        target.chmod(0o600)
    except Exception:
        try:
            part.unlink()
        except OSError:
            pass
        raise
    state = {
        **state,
        "downloaded": {"path": str(target), "sha256": digest.hexdigest(), "bytes": total, "at": _now()},
        "error": None,
    }
    _write_state(home, state)
    return {"ok": True, "path": str(target), "sha256": digest.hexdigest(), "bytes": total}


def status(home: str | Path) -> dict[str, Any]:
    home = Path(home).expanduser()
    state = read_state(home)
    return {
        "ok": True,
        "current": current_version(home),
        "checked_at": state.get("checked_at"),
        "available": bool(state.get("available")),
        "latest": state.get("latest"),
        "downloaded": state.get("downloaded"),
        "error": state.get("error"),
    }
