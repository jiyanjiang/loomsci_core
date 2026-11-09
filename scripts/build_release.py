#!/usr/bin/env python3
"""Build a portable loomsci_core release package.

The package is a zip with a deterministic top-level directory, build metadata,
an upgrade manifest, and a SHA-256 sidecar. Signing is optional and requires an
Ed25519 private key path; no key is shipped in this repository.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGE_NAME = "loomsci_core"
INCLUDE_DIRS = ("core", "cli", "presets", "docs", "scripts")
INCLUDE_FILES = (
    "pyproject.toml",
    "requirements.txt",
    "VERSION",
    "README.md",
    "README.zh-CN.md",
    "LICENSE",
    "NOTICE",
    "SECURITY.md",
    "CONTRIBUTING.md",
    "AGENTS.md",
    "install.sh",
    "install.ps1",
)
PRESERVE = (
    "data/",
    "agents/",
    "packs/",
    "logs/",
    "runtime/",
    "config.yaml",
)
FORBID = (
    "data/data.db",
    "agents/",
    "config.yaml",
)


def version() -> str:
    return (ROOT / "VERSION").read_text(encoding="utf-8").strip() or "0.0.0"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build_info() -> dict:
    return {
        "product": PACKAGE_NAME,
        "version": version(),
        "built_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "source": "loomsci_core public repository",
        "included": list(INCLUDE_DIRS) + list(INCLUDE_FILES),
    }


def upgrade_manifest() -> dict:
    return {
        "manifest_schema": 1,
        "product": PACKAGE_NAME,
        "package_version": version(),
        "replace": ["core/", "cli/", "presets/", "docs/", "scripts/"],
        "preserve": list(PRESERVE),
        "forbid_overwrite": list(FORBID),
    }


def _add_tree(zf: zipfile.ZipFile, source: Path, base: str) -> None:
    for path in sorted(source.rglob("*")):
        if not path.is_file():
            continue
        if any(part in {"__pycache__", ".pytest_cache"} for part in path.parts):
            continue
        rel = path.relative_to(source).as_posix()
        zf.write(path, f"{base}/{rel}")


def build(
    out_dir: Path, signing_key: str | None = None, base_url: str = ""
) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    ver = version()
    archive = out_dir / f"{PACKAGE_NAME}-{ver}.zip"
    fd, tmp_name = tempfile.mkstemp(prefix="loomsci-release-", suffix=".zip")
    os.close(fd)
    tmp = Path(tmp_name)
    root = PACKAGE_NAME
    try:
        with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for directory in INCLUDE_DIRS:
                source = ROOT / directory
                if source.is_dir():
                    _add_tree(zf, source, f"{root}/{directory}")
            for name in INCLUDE_FILES:
                path = ROOT / name
                if path.is_file():
                    zf.write(path, f"{root}/{name}")
            zf.writestr(
                f"{root}/BUILD_INFO.json",
                json.dumps(build_info(), ensure_ascii=False, indent=2),
            )
            zf.writestr(
                f"{root}/upgrade-manifest.json",
                json.dumps(upgrade_manifest(), ensure_ascii=False, indent=2),
            )
        os.replace(tmp, archive)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise

    digest = sha256_file(archive)
    (out_dir / f"{archive.name}.sha256").write_text(
        f"{digest}  {archive.name}\n", encoding="utf-8"
    )
    signature = ""
    if signing_key:
        try:
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.primitives.asymmetric.ed25519 import (
                Ed25519PrivateKey,
            )

            raw = Path(signing_key).expanduser().read_bytes()
            key = Ed25519PrivateKey.from_private_bytes(raw)
            sig_path = archive.with_suffix(archive.suffix + ".sig")
            sig_path.write_bytes(key.sign(archive.read_bytes()))
            signature = sig_path.name
        except Exception as exc:
            raise SystemExit(f"signing failed: {exc}") from exc

    latest = {
        "product": PACKAGE_NAME,
        "version": ver,
        "channel": "preview",
        "url": f"{base_url.rstrip('/')}/{archive.name}" if base_url else archive.name,
        "bytes": archive.stat().st_size,
        "sha256": digest,
        "published_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "signature": signature,
    }
    (out_dir / "latest.json").write_text(
        json.dumps(latest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {"archive": str(archive), "sha256": digest, "latest": latest}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="build_release")
    parser.add_argument("--out", default=str(ROOT / "dist"))
    parser.add_argument("--signing-key", help="raw Ed25519 private key file")
    parser.add_argument("--base-url", default="", help="public URL prefix for the package")
    args = parser.parse_args(argv)
    result = build(Path(args.out), args.signing_key, args.base_url)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
