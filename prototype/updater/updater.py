#!/usr/bin/env python3
"""Minimal signed Core updater prototype.

Not product code. Verifies a signed package, backs up, stops Core, atomically
replaces a payload marker, starts Core, and rolls back on failure.
"""

from __future__ import annotations

import argparse
import json
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORE = ROOT / "core_v0"
CLI = CORE / "cli.py"
TRUST = ROOT / "signing" / "trust.py"
sys.path.insert(0, str(CORE))
import backup as backup_store  # noqa: E402


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def run(*args: str) -> tuple[int, str]:
    result = subprocess.run(args, text=True, capture_output=True)
    return result.returncode, (result.stdout + result.stderr).strip()


def health(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/v1/health", timeout=1) as response:
            return response.status == 200
    except Exception:
        return False


def cli(home: Path, *args: str) -> tuple[int, str]:
    return run(sys.executable, str(CLI), "--home", str(home), *args)


def apply(package: Path, home: Path, trust: Path, port: int) -> dict:
    package = package.resolve()
    manifest_path = package / "manifest.json"
    sig = package / "manifest.sig"
    payload = package / "payload.bin"
    if not manifest_path.is_file() or not sig.is_file() or not payload.is_file():
        raise SystemExit("package_incomplete")
    code, out = run(
        sys.executable, str(TRUST), "verify",
        "--manifest", str(manifest_path), "--sig", str(sig),
        "--payload", str(payload), "--trust", str(trust),
    )
    if code != 0:
        raise SystemExit("package_verify_failed: " + out)
    current = home / "core.current"
    previous = home / "core.previous"
    next_file = home / "core.next"
    if current.is_file():
        shutil.copy2(current, previous)
    code, out = cli(home, "stop", "--json")
    if code != 0:
        raise SystemExit("core_stop_failed: " + out)
    try:
        backup_store.create(home)
    except Exception as exc:
        cli(home, "--port", str(port), "start", "--json")
        raise SystemExit("backup_failed: " + str(exc))
    try:
        shutil.copy2(payload, next_file)
        next_file.replace(current)
        code, out = cli(home, "--port", str(port), "start", "--json")
        if code != 0 or not health(port):
            raise RuntimeError("core_start_failed: " + out)
        return {"updated": True, "home": str(home), "payload": str(current)}
    except Exception:
        if previous.is_file():
            previous.replace(current)
        cli(home, "--port", str(port), "start", "--json")
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", required=True)
    parser.add_argument("--home", required=True)
    parser.add_argument("--trust", required=True)
    parser.add_argument("--port", type=int, default=8795)
    args = parser.parse_args()
    try:
        result = apply(Path(args.package), Path(args.home), Path(args.trust), args.port)
    except SystemExit as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 1
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 1
    print(json.dumps({"ok": True, **result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
