"""Signed, staged Core self-update.

Manifest fields:
  product, version, channel, url, sha256, min_core, notes_url, signature

The signature is Ed25519 over canonical JSON of every field except signature.
The package is a zip containing a top-level ``loomsci_core/`` directory.

This module owns the update state machine. The actual code/data swap is
performed by ``apply_package``; it stops Core, creates a data backup and a code
snapshot, swaps the package, starts Core, and restores both code and data on
failure.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from .version import __version__

PRODUCT = "loomsci_core"
PUBLIC_KEY_PATH = Path(__file__).resolve().parent / "update_public_key.pem"
API_MANIFEST_URL = (
    "https://api.github.com/repos/jiyanjiang/loomsci_core/contents/"
    "releases/latest.json?ref=minimal-v0"
)
RAW_MANIFEST_URL = (
    "https://raw.githubusercontent.com/jiyanjiang/loomsci_core/"
    "minimal-v0/releases/latest.json"
)
DEFAULT_MANIFEST_URL = os.environ.get("LOOMSCI_UPDATE_URL", API_MANIFEST_URL)
LEGACY_DEFAULT_MANIFEST_URL = (
    "https://raw.githubusercontent.com/jiyanjiang/loomsci_core/main/releases/latest.json"
)
STATE_VERSION = 1

DEFAULT_STATE: dict[str, Any] = {
    "enabled": True,
    "mode": "download",          # notify | download
    "channel": "stable",
    "manifest_url": DEFAULT_MANIFEST_URL,
    "last_check_at": "",
    "last_check_result": "",
    "latest": None,
    "downloaded": None,
    "pending_version": "",
    "failed_versions": {},
    "last_error": "",
    "last_result": "",
}


class UpdateError(RuntimeError):
    pass


def _version_key(value: str) -> tuple:
    """Semver-ish key: stable > prerelease; rc.5 > rc.4."""
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.\-]+))?$", str(value or "").strip())
    if not match:
        return (0, 0, 0, 0, ())
    major, minor, patch = int(match.group(1)), int(match.group(2)), int(match.group(3))
    pre = match.group(4)
    if pre is None:
        return (major, minor, patch, 1, ())
    parts = tuple((0, int(part)) if part.isdigit() else (1, part) for part in re.split(r"[.\-]", pre))
    return (major, minor, patch, 0, parts)


def _version_parts(value: str) -> tuple[int, ...]:
    key = _version_key(value)
    return (key[0], key[1], key[2], key[3])


def is_newer(candidate: str, current: str = __version__) -> bool:
    return _version_key(candidate) > _version_key(current)


def canonical(manifest: dict[str, Any]) -> bytes:
    data = {key: value for key, value in manifest.items() if key != "signature"}
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sign_manifest(manifest: dict[str, Any], private_key_path: Path) -> str:
    key = serialization.load_pem_private_key(private_key_path.read_bytes(), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise UpdateError("update key is not Ed25519")
    return base64.b64encode(key.sign(canonical(manifest))).decode("ascii")


def verify_signature(manifest: dict[str, Any], public_key_path: Path | None = None) -> None:
    signature = str(manifest.get("signature") or "")
    if not signature:
        raise UpdateError("manifest signature missing")
    path = public_key_path or Path(os.environ.get("LOOMSCI_UPDATE_PUBLIC_KEY", PUBLIC_KEY_PATH))
    if not path.is_file():
        raise UpdateError("update public key missing")
    key = serialization.load_pem_public_key(path.read_bytes())
    if not isinstance(key, Ed25519PublicKey):
        raise UpdateError("update public key is not Ed25519")
    try:
        key.verify(base64.b64decode(signature), canonical(manifest))
    except Exception as exc:  # noqa: BLE001 - signature boundary
        raise UpdateError("manifest signature invalid") from exc


def validate_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    if manifest.get("product") != PRODUCT:
        raise UpdateError("wrong product")
    version = str(manifest.get("version") or "")
    if not version:
        raise UpdateError("manifest version missing")
    if not manifest.get("sha256"):
        raise UpdateError("manifest sha256 missing")
    verify_signature(manifest)
    return manifest


def check_manifest(manifest: dict[str, Any], current: str = __version__) -> dict[str, Any]:
    validate_manifest(manifest)
    version = str(manifest.get("version") or "")
    if not is_newer(version, current):
        raise UpdateError(f"version {version} is not newer than {current}")
    min_core = str(manifest.get("min_core") or "0")
    # min_core is a compatibility floor, not a release ordering. A 0.2.0
    # floor accepts 0.2.0-rc.N; use the numeric base for this check.
    if _version_key(min_core)[:3] > _version_key(current)[:3]:
        raise UpdateError(f"requires Core {min_core} or newer")
    return manifest


def _http_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": f"loomsci-core/{__version__}",
            "Accept": "application/vnd.github+json, application/json",
            "Cache-Control": "no-cache",
        },
    )
    last: Exception | None = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError, ValueError) as exc:
            last = exc
            if attempt < 2:
                time.sleep(0.6 * (attempt + 1))
    raise UpdateError(f"manifest fetch failed: {last}") from last


def _decode_manifest(data: dict[str, Any]) -> dict[str, Any]:
    # GitHub Contents API wraps the file as base64; raw URLs return it directly.
    if data.get("encoding") == "base64" and isinstance(data.get("content"), str):
        raw = base64.b64decode(data["content"]).decode("utf-8")
        return json.loads(raw)
    return data


def load_manifest(source: str) -> dict[str, Any]:
    if source.startswith(("http://", "https://")):
        if not source.startswith("https://") and os.environ.get("LOOMSCI_UPDATE_ALLOW_HTTP") != "1":
            raise UpdateError("update manifest must use HTTPS")
        urls = [source]
        if source == DEFAULT_MANIFEST_URL:
            urls.append(RAW_MANIFEST_URL)
        elif source == RAW_MANIFEST_URL:
            urls.append(API_MANIFEST_URL)
        last: Exception | None = None
        for url in dict.fromkeys(urls):
            try:
                return _decode_manifest(_http_json(url))
            except Exception as exc:  # noqa: BLE001 - network boundary
                last = exc
        raise UpdateError(f"manifest fetch failed: {last}") from last
    return json.loads(Path(source).expanduser().read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _api_contents_url(raw_url: str) -> str | None:
    match = re.match(
        r"^https://raw\.githubusercontent\.com/([^/]+)/([^/]+)/([^/]+)/(.+)$",
        raw_url,
    )
    if not match:
        return None
    owner, repo, branch, path = match.groups()
    return f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={branch}"


def download_package(source: str, destination: Path) -> Path:
    if source.startswith(("http://", "https://")):
        if not source.startswith("https://") and os.environ.get("LOOMSCI_UPDATE_ALLOW_HTTP") != "1":
            raise UpdateError("update package must use HTTPS")
        request = urllib.request.Request(
            source, headers={"User-Agent": f"loomsci-core/{__version__}"}
        )
        last: Exception | None = None
        for attempt in range(3):
            try:
                with urllib.request.urlopen(request, timeout=120) as response, destination.open("wb") as out:
                    shutil.copyfileobj(response, out)
                return destination
            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
                last = exc
                destination.unlink(missing_ok=True)
                if attempt < 2:
                    time.sleep(1.0 * (attempt + 1))
        # raw.githubusercontent.com can reset connections. GitHub Contents API
        # serves the same versioned file as base64; use it as a bounded fallback.
        api_url = _api_contents_url(source)
        if api_url:
            try:
                data = _http_json(api_url)
                if data.get("encoding") == "base64" and data.get("content"):
                    destination.write_bytes(base64.b64decode(data["content"]))
                    return destination
            except Exception as exc:  # noqa: BLE001 - fallback boundary
                last = exc
        raise UpdateError(f"package download failed: {last}") from last
    shutil.copy2(Path(source).expanduser(), destination)
    return destination


def verify_package(path: Path, manifest: dict[str, Any]) -> None:
    if not path.is_file():
        raise UpdateError("update package missing")
    if sha256_file(path) != str(manifest.get("sha256") or "").lower():
        raise UpdateError("package sha256 mismatch")
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
    if not any(name == "loomsci_core/__init__.py" for name in names):
        raise UpdateError("package is missing loomsci_core/__init__.py")
    verify_signature(manifest)


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def state_path(home: Path) -> Path:
    return home.expanduser() / "updates" / "update.json"


def journal_path(home: Path) -> Path:
    return home.expanduser() / "updates" / "journal.json"


def _load_state(home: Path) -> dict[str, Any]:
    data = dict(DEFAULT_STATE)
    path = state_path(home)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            data.update(raw)
    except (OSError, ValueError):
        pass
    if not isinstance(data.get("failed_versions"), dict):
        data["failed_versions"] = {}
    if data.get("manifest_url") in {LEGACY_DEFAULT_MANIFEST_URL, RAW_MANIFEST_URL}:
        data["manifest_url"] = DEFAULT_MANIFEST_URL
    if not data.get("manifest_url"):
        data["manifest_url"] = DEFAULT_MANIFEST_URL
    return data


def _save_state(home: Path, state: dict[str, Any]) -> None:
    path = state_path(home)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    try:
        tmp.chmod(0o600)
    except OSError:
        pass
    os.replace(tmp, path)


def _journal(home: Path) -> dict[str, Any]:
    try:
        raw = json.loads(journal_path(home).read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}
    except (OSError, ValueError):
        return {}


def _write_journal(home: Path, phase: str, **extra: Any) -> None:
    path = journal_path(home)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"phase": phase.upper(), "at": _now(), **extra}
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _install_lock_path(home: Path) -> Path:
    return home.expanduser() / "updates" / "install.lock"


def _acquire_install_lock(home: Path) -> Path:
    path = _install_lock_path(home)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        try:
            age = time.time() - path.stat().st_mtime
        except OSError:
            age = 0
        if age > 30 * 60:
            path.unlink(missing_ok=True)
            return _acquire_install_lock(home)
        raise UpdateError("update already running")
    try:
        os.write(fd, f"{os.getpid()} {time.time():.0f}\n".encode())
    finally:
        os.close(fd)
    return path


def _release_install_lock(path: Path) -> None:
    path.unlink(missing_ok=True)


def _blocked(state: dict[str, Any], version: str) -> bool:
    return bool(version) and version in (state.get("failed_versions") or {})


def _state_name(state: dict[str, Any], phase: str) -> str:
    current = __version__
    latest = state.get("latest") or {}
    downloaded = state.get("downloaded") or {}
    latest_v = str(latest.get("version") or "")
    downloaded_v = str(downloaded.get("version") or "")
    if not state.get("manifest_url") and not latest_v:
        return "unconfigured"
    if phase in {"ROLLED_BACK", "FAILED", "ROLLBACK"}:
        return "failed"
    if phase in {"STOPPING", "BACKUP", "STAGING", "SWAPPING", "STARTING"}:
        return "applying"
    if state.get("last_result") == "applying":
        return "applying"
    if downloaded_v and is_newer(downloaded_v, current):
        return "downloaded"
    if latest_v and is_newer(latest_v, current):
        return "available"
    if latest_v:
        return "current"
    return "unchecked"


def status(home: Path) -> dict[str, Any]:
    home = home.expanduser()
    state = _load_state(home)
    journal = _journal(home)
    latest = state.get("latest") or {}
    downloaded = state.get("downloaded") or {}
    phase = str(journal.get("phase") or "")
    current = __version__
    latest_v = str(latest.get("version") or "")
    downloaded_v = str(downloaded.get("version") or "")
    state_name = _state_name(state, phase)
    configured = bool(state.get("manifest_url"))
    last_error = str(state.get("last_error") or "") if configured else ""
    if state_name == "failed" and not last_error:
        last_error = str(journal.get("error") or "")
    last_check_at = str(state.get("last_check_at") or "") if configured else ""
    return {
        "ok": True,
        "product": PRODUCT,
        "current": current,
        "latest": latest_v,
        "available": bool(latest_v and is_newer(latest_v, current)),
        "state": state_name,
        "enabled": bool(state.get("enabled", True)),
        "mode": state.get("mode", "download"),
        "channel": state.get("channel", "stable"),
        "manifest_url": state.get("manifest_url", ""),
        "last_check_at": last_check_at,
        "last_result": state.get("last_result", ""),
        "last_error": last_error,
        "downloaded": str(downloaded.get("path") or ""),
        "downloaded_version": downloaded_v,
        "pending_version": state.get("pending_version", ""),
        "blocked": _blocked(state, latest_v),
        "blocked_versions": sorted((state.get("failed_versions") or {}).keys()),
        "notes_url": latest.get("notes_url", ""),
        "journal": journal,
    }


def settings(home: Path, **changes: Any) -> dict[str, Any]:
    state = _load_state(home)
    for key in ("enabled", "mode", "channel", "manifest_url"):
        if key in changes and changes[key] is not None:
            state[key] = changes[key]
    if state.get("mode") == "auto":
        state["mode"] = "download"
    _save_state(home, state)
    return status(home)


def check(home: Path, source: str | None = None, *, force: bool = False) -> dict[str, Any]:
    state = _load_state(home)
    if not state.get("enabled", True) and not force:
        return {**status(home), "ok": False, "error": "updates disabled"}
    source = source or str(state.get("manifest_url") or "") or DEFAULT_MANIFEST_URL
    if not source:
        state["last_check_at"] = _now()
        state["last_check_result"] = "unconfigured"
        state["last_error"] = ""
        state["last_result"] = "unconfigured"
        _save_state(home, state)
        return {**status(home), "ok": False, "error": "no_manifest_url"}
    try:
        manifest = load_manifest(source)
        validate_manifest(manifest)
        state["latest"] = manifest
        state["last_check_at"] = _now()
        state["last_check_result"] = "checked"
        state["last_error"] = ""
        state["last_result"] = "checked"
        available = is_newer(str(manifest.get("version") or ""), __version__)
        if available and _blocked(state, str(manifest.get("version") or "")):
            state["last_result"] = "blocked"
        _save_state(home, state)
        return {"ok": True, "available": available, **status(home)}
    except Exception as exc:  # noqa: BLE001 - network/update boundary
        state["last_check_at"] = _now()
        state["last_check_result"] = "error"
        state["last_error"] = str(exc)
        _save_state(home, state)
        return {**status(home), "ok": False, "error": str(exc)}


def download(home: Path, manifest: dict[str, Any] | None = None, *, force: bool = False) -> dict[str, Any]:
    state = _load_state(home)
    manifest = manifest or state.get("latest")
    if not isinstance(manifest, dict):
        return {**status(home), "ok": False, "error": "no_update_manifest"}
    try:
        validate_manifest(manifest)
        version = str(manifest.get("version") or "")
        if not is_newer(version, __version__):
            return {**status(home), "ok": False, "error": "not_newer"}
        if _blocked(state, version) and not force:
            return {**status(home), "ok": False, "error": "version_blocked", "blocked": True}
        if not manifest.get("url"):
            raise UpdateError("manifest url missing")
        target = home.expanduser() / "updates" / f"loomsci_core-{version}.zip"
        target.parent.mkdir(parents=True, exist_ok=True)
        download_package(str(manifest["url"]), target)
        verify_package(target, manifest)
        state["downloaded"] = {
            "version": version,
            "path": str(target),
            "sha256": str(manifest.get("sha256") or ""),
            "url": str(manifest.get("url") or ""),
        }
        state["last_result"] = "downloaded"
        state["last_error"] = ""
        _save_state(home, state)
        return {"ok": True, **status(home)}
    except Exception as exc:  # noqa: BLE001 - network/hash boundary
        state["last_error"] = str(exc)
        state["last_result"] = "download_failed"
        _save_state(home, state)
        return {**status(home), "ok": False, "error": str(exc)}


def _stop(home: Path) -> None:
    from . import cli
    cli.stop(home)


def _start(home: Path, port: int) -> None:
    from . import cli
    cli.start(home, port)


def _restore_code(target: Path, old: Path) -> None:
    if target.exists():
        shutil.rmtree(target)
    if old.exists():
        old.rename(target)


def _apply_package_locked(
    package: Path,
    manifest: dict[str, Any],
    *,
    home: Path,
    port: int,
    install_root: Path | None = None,
) -> dict[str, Any]:
    """Verify, stop, back up data, swap code, start, and restore on failure."""
    verify_package(package, manifest)
    install_root = install_root or Path(__file__).resolve().parent.parent
    target = install_root / "loomsci_core"
    if not target.is_dir():
        raise UpdateError("installed Core directory missing")
    updates = home.expanduser() / "updates"
    updates.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    snapshot = updates / f"code-{__version__}-{stamp}"
    data_backup: Path | None = None
    old = install_root / f"loomsci_core.pre-{stamp}"
    replaced = False
    from . import backup as backup_store

    _write_journal(home, "PREFLIGHT", version=manifest.get("version"), package=str(package))
    try:
        _write_journal(home, "STOPPING")
        _stop(home)
        _write_journal(home, "BACKUP")
        data_backup = backup_store.create(home)
        shutil.copytree(target, snapshot)
        _write_journal(home, "STAGING")
        with tempfile.TemporaryDirectory(prefix="loomsci-update-") as tmp:
            with zipfile.ZipFile(package) as archive:
                archive.extractall(tmp)
            staged = Path(tmp) / "loomsci_core"
            if not staged.is_dir():
                raise UpdateError("package payload missing")
            _write_journal(home, "SWAPPING")
            target.rename(old)
            staged.rename(target)
            replaced = True
            _write_journal(home, "STARTING")
            _start(home, port)
        _write_journal(home, "COMMITTED", version=manifest.get("version"))
        return {
            "ok": True,
            "version": manifest["version"],
            "package": str(package),
            "data_backup": str(data_backup),
            "code_snapshot": str(snapshot),
        }
    except BaseException as exc:
        _write_journal(home, "ROLLBACK", error=str(exc))
        _stop(home)
        if replaced:
            try:
                _restore_code(target, old)
            except Exception as restore_exc:  # noqa: BLE001 - rollback boundary
                raise UpdateError(f"code rollback failed: {restore_exc}") from exc
        if data_backup is not None:
            try:
                backup_store.restore_in_place(home, data_backup)
            except Exception as restore_exc:  # noqa: BLE001 - rollback boundary
                raise UpdateError(f"data rollback failed: {restore_exc}") from exc
        try:
            _start(home, port)
        except Exception as rollback_exc:  # noqa: BLE001 - rollback boundary
            _write_journal(home, "FAILED", error=str(rollback_exc), failed_phase="START")
            raise UpdateError(
                f"update failed and rollback start failed: {rollback_exc}"
            ) from exc
        _write_journal(home, "ROLLED_BACK", error=str(exc))
        raise UpdateError(f"update failed and was rolled back: {exc}") from exc


def apply_package(
    package: Path,
    manifest: dict[str, Any],
    *,
    home: Path,
    port: int,
    install_root: Path | None = None,
) -> dict[str, Any]:
    lock = _acquire_install_lock(home)
    try:
        return _apply_package_locked(
            package, manifest, home=home, port=port, install_root=install_root
        )
    finally:
        _release_install_lock(lock)


def _record_failure(home: Path, state: dict[str, Any], version: str, error: str) -> None:
    failed = dict(state.get("failed_versions") or {})
    record = dict(failed.get(version) or {})
    record["count"] = int(record.get("count") or 0) + 1
    record["at"] = _now()
    record["error"] = str(error)[:300]
    failed[version] = record
    state["failed_versions"] = failed
    state["downloaded"] = None
    state["pending_version"] = ""
    state["last_result"] = "rolled_back"
    state["last_error"] = f"{version} 安装失败，已回滚；自动重试已暂停，可手动重试"
    _save_state(home, state)


def apply_pending(home: Path, port: int) -> dict[str, Any]:
    state = _load_state(home)
    downloaded = state.get("downloaded") or {}
    version = str(downloaded.get("version") or "")
    package = Path(str(downloaded.get("path") or ""))
    manifest = state.get("latest") or {}
    if not version or not package.is_file():
        return {**status(home), "ok": False, "error": "no_downloaded_package"}
    if str(manifest.get("version") or "") != version:
        return {**status(home), "ok": False, "error": "manifest_package_mismatch"}
    state["pending_version"] = version
    state["last_result"] = "applying"
    state["last_error"] = ""
    _save_state(home, state)
    try:
        result = apply_package(package, manifest, home=home, port=port)
    except UpdateError as exc:
        if "already running" in str(exc):
            return {**status(home), "ok": False, "error": str(exc)}
        _record_failure(home, _load_state(home), version, str(exc))
        return {**status(home), "ok": False, "error": str(exc)}
    except Exception as exc:  # noqa: BLE001 - update boundary
        _record_failure(home, _load_state(home), version, str(exc))
        return {**status(home), "ok": False, "error": str(exc)}
    state = _load_state(home)
    state["downloaded"] = None
    state["pending_version"] = ""
    state["last_result"] = "committed"
    state["last_error"] = ""
    _save_state(home, state)
    return {"ok": True, **result, **status(home)}


def apply_async(home: Path, port: int) -> dict[str, Any]:
    state = _load_state(home)
    if state.get("last_result") == "applying" or state.get("pending_version"):
        return {**status(home), "ok": False, "error": "update already running"}
    downloaded = state.get("downloaded") or {}
    if not downloaded.get("path") or not Path(str(downloaded["path"])).is_file():
        return {**status(home), "ok": False, "error": "no_downloaded_package"}
    version = str(downloaded.get("version") or "")
    log = journal_path(home).parent / "updater.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    kwargs: dict[str, Any] = {}
    if os.name == "nt":
        kwargs["creationflags"] = (
            getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            | getattr(subprocess, "DETACHED_PROCESS", 0)
            | getattr(subprocess, "CREATE_BREAKAWAY_FROM_JOB", 0)
        )
    else:
        kwargs["start_new_session"] = True
    with log.open("ab") as handle:
        handle.write(f"\n=== {_now()} apply {version} ===\n".encode())
        handle.flush()
        subprocess.Popen(
            [sys.executable, "-m", "loomsci_core", "--home", str(home), "--port", str(port), "update", "install"],
            cwd=Path(__file__).resolve().parent.parent,
            stdin=subprocess.DEVNULL, stdout=handle, stderr=handle,
            **kwargs,
        )
    state["pending_version"] = version
    state["last_result"] = "applying"
    state["last_error"] = ""
    _save_state(home, state)
    return {"ok": True, "started": True, **status(home)}


_scheduler_started = False
_scheduler_lock = threading.Lock()


def tick(home: Path, port: int) -> dict[str, Any]:
    state = _load_state(home)
    if not state.get("enabled", True) or not state.get("manifest_url"):
        return status(home)
    result = check(home)
    if result.get("available") and not result.get("blocked"):
        result = download(home)
    return result


def start_scheduler(home: Path, port: int) -> None:
    global _scheduler_started
    with _scheduler_lock:
        if _scheduler_started or os.environ.get("LOOMSCI_DISABLE_UPDATE_SCHEDULER") == "1":
            return
        _scheduler_started = True

    def loop() -> None:
        # Do not race startup; then check at most once every six hours.
        time.sleep(60)
        while True:
            try:
                tick(home, port)
            except Exception as exc:  # noqa: BLE001 - background boundary
                log = journal_path(home).parent / "updater.log"
                try:
                    log.parent.mkdir(parents=True, exist_ok=True)
                    with log.open("a", encoding="utf-8") as handle:
                        handle.write(f"{_now()} scheduler error: {exc}\n")
                except OSError:
                    pass
            time.sleep(6 * 60 * 60)

    threading.Thread(target=loop, name="loomsci-update", daemon=True).start()
