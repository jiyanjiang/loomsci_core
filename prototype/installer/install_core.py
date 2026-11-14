#!/usr/bin/env python3
"""Install a signed Core package into a new home.

Not a production installer. Validates signature, extracts payload, creates a
venv, installs requirements, and writes a launcher.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRUST = Path(os.environ.get("LOOMSCI_TRUST_SCRIPT", str(Path(__file__).with_name("trust.py"))))


def run(*args: str) -> tuple[int, str]:
    result = subprocess.run(args, text=True, capture_output=True)
    return result.returncode, result.stdout + result.stderr


def safe_extract(archive: Path, target: Path) -> None:
    with tarfile.open(archive, "r:gz") as tar:
        for member in tar.getmembers():
            member_path = (target / member.name).resolve()
            if not str(member_path).startswith(str(target.resolve()) + os.sep):
                raise SystemExit("unsafe_tar_path")
        tar.extractall(target, filter="data")


def install(package: Path, home: Path, trust: Path, uv: Path | None) -> dict:
    package = package.resolve()
    home = home.expanduser()
    if home.exists():
        raise SystemExit(f"target_exists: {home}")
    manifest = package / "manifest.json"
    sig = package / "manifest.sig"
    payload = package / "payload.tar.gz"
    if not (manifest.is_file() and sig.is_file() and payload.is_file()):
        raise SystemExit("package_incomplete")
    code, out = run(
        sys.executable, str(TRUST), "verify",
        "--manifest", str(manifest), "--sig", str(sig),
        "--payload", str(payload), "--trust", str(trust),
    )
    if code != 0:
        raise SystemExit("package_verify_failed: " + out)
    tmp = home.with_name(home.name + ".tmp-" + str(os.getpid()))
    if tmp.exists():
        shutil.rmtree(tmp)
    try:
        tmp.mkdir(parents=True)
        safe_extract(payload, tmp / "core")
        venv_dir = tmp / "venv"
        if uv:
            code, out = run(str(uv), "venv", "--python", "3.12", str(venv_dir))
        else:
            code, out = run(sys.executable, "-m", "venv", str(venv_dir))
        if code != 0:
            raise SystemExit("venv_failed: " + out)
        python = venv_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        final_python = home / "venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        requirements = tmp / "core" / "requirements-core.txt"
        if requirements.is_file():
            if uv:
                code, out = run(str(uv), "pip", "install", "--python", str(python), "-r", str(requirements))
            else:
                code, out = run(str(python), "-m", "pip", "install", "-r", str(requirements))
            if code != 0:
                raise SystemExit("dependencies_failed: " + out)
        bin_dir = tmp / "bin"
        bin_dir.mkdir()
        if os.name == "nt":
            launcher = bin_dir / "loomsci-v0.cmd"
            launcher.write_text(
                f'@echo off\r\nset "PYTHONPATH={home}\\core"\r\n"{final_python}" -m loomsci_core %*\r\n',
                encoding="utf-8",
            )
        else:
            launcher = bin_dir / "loomsci-v0"
            launcher.write_text(
                f'#!/bin/sh\nPYTHONPATH="{home}/core" exec "{final_python}" -m loomsci_core "$@"\n',
                encoding="utf-8",
            )
            launcher.chmod(0o755)
        install_meta = {
            "format": "loomsci-install/1",
            "version": json.loads(manifest.read_text())["version"],
            "home": str(home),
            "python": str(final_python),
            "launcher": str(home / "bin" / launcher.name),
        }
        (tmp / "install.json").write_text(json.dumps(install_meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.rename(home)
        return install_meta
    except Exception:
        if tmp.exists():
            shutil.rmtree(tmp)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", required=True)
    parser.add_argument("--home", required=True)
    parser.add_argument("--trust", required=True)
    parser.add_argument("--uv")
    args = parser.parse_args()
    try:
        result = install(Path(args.package), Path(args.home), Path(args.trust),
                         Path(args.uv) if args.uv else None)
    except SystemExit as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 1
    print(json.dumps({"ok": True, **result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
