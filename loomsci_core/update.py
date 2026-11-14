"""Signed, staged Core self-update.

Manifest:
  product, version, channel, url, sha256, min_core, signature

The signature is Ed25519 over canonical JSON of every field except signature.
The package is a zip containing a top-level ``loomsci_core/`` directory.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from .version import __version__

PRODUCT = "loomsci_core"
PUBLIC_KEY_PATH = Path(__file__).resolve().parent / "update_public_key.pem"


class UpdateError(RuntimeError):
    pass


def _version_parts(value: str) -> tuple[int, ...]:
    parts = []
    for chunk in str(value).replace("-", ".").split("."):
        digits = "".join(ch for ch in chunk if ch.isdigit())
        parts.append(int(digits or 0))
    return tuple(parts)


def is_newer(candidate: str, current: str = __version__) -> bool:
    return _version_parts(candidate) > _version_parts(current)


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


def check_manifest(manifest: dict[str, Any], current: str = __version__) -> dict[str, Any]:
    if manifest.get("product") != PRODUCT:
        raise UpdateError("wrong product")
    version = str(manifest.get("version") or "")
    if not version:
        raise UpdateError("manifest version missing")
    if not is_newer(version, current):
        raise UpdateError(f"version {version} is not newer than {current}")
    min_core = str(manifest.get("min_core") or "0")
    if _version_parts(min_core) > _version_parts(current):
        raise UpdateError(f"requires Core {min_core} or newer")
    if not manifest.get("sha256"):
        raise UpdateError("manifest sha256 missing")
    verify_signature(manifest)
    return manifest


def load_manifest(source: str) -> dict[str, Any]:
    if source.startswith(("http://", "https://")):
        if not source.startswith("https://") and os.environ.get("LOOMSCI_UPDATE_ALLOW_HTTP") != "1":
            raise UpdateError("update manifest must use HTTPS")
        with urllib.request.urlopen(source, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    return json.loads(Path(source).read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_package(source: str, destination: Path) -> Path:
    if source.startswith(("http://", "https://")):
        if not source.startswith("https://") and os.environ.get("LOOMSCI_UPDATE_ALLOW_HTTP") != "1":
            raise UpdateError("update package must use HTTPS")
        with urllib.request.urlopen(source, timeout=60) as response, destination.open("wb") as out:
            shutil.copyfileobj(response, out)
    else:
        shutil.copy2(source, destination)
    return destination


def verify_package(path: Path, manifest: dict[str, Any]) -> None:
    if sha256_file(path) != str(manifest.get("sha256") or "").lower():
        raise UpdateError("package sha256 mismatch")
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
    if not any(name == "loomsci_core/__init__.py" for name in names):
        raise UpdateError("package is missing loomsci_core/__init__.py")
    verify_signature(manifest)


def _stop(home: Path) -> None:
    from . import cli
    cli.stop(home)


def _start(home: Path, port: int) -> None:
    from . import cli
    cli.start(home, port)


def apply_package(
    package: Path,
    manifest: dict[str, Any],
    *,
    home: Path,
    port: int,
    install_root: Path | None = None,
) -> dict[str, Any]:
    """Verify, back up, swap code, start, and roll back on failure."""
    verify_package(package, manifest)
    install_root = install_root or Path(__file__).resolve().parent.parent
    target = install_root / "loomsci_core"
    if not target.is_dir():
        raise UpdateError("installed Core directory missing")
    updates = home / "updates"
    updates.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    snapshot = updates / f"code-{__version__}-{stamp}"
    data_backup = None
    from . import backup as backup_store
    data_backup = backup_store.create(home)
    shutil.copytree(target, snapshot)

    with tempfile.TemporaryDirectory(prefix="loomsci-update-") as tmp:
        with zipfile.ZipFile(package) as archive:
            archive.extractall(tmp)
        staged = Path(tmp) / "loomsci_core"
        if not staged.is_dir():
            raise UpdateError("package payload missing")
        _stop(home)
        replaced = False
        try:
            old = install_root / f"loomsci_core.pre-{stamp}"
            target.rename(old)
            staged.rename(target)
            replaced = True
            _start(home, port)
            return {
                "ok": True,
                "version": manifest["version"],
                "package": str(package),
                "data_backup": str(data_backup),
                "code_snapshot": str(snapshot),
            }
        except BaseException as exc:
            _stop(home)
            if replaced:
                if target.exists():
                    shutil.rmtree(target)
                old.rename(target)
            try:
                _start(home, port)
            except Exception as rollback_exc:  # noqa: BLE001 - rollback boundary
                raise UpdateError(
                    f"update failed and rollback start failed: {rollback_exc}"
                ) from exc
            raise UpdateError(f"update failed and was rolled back: {exc}") from exc
