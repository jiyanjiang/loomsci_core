#!/usr/bin/env python3
"""Minimal Core App Host prototype for the process contract.

Not product code. It exists to validate:
install -> start -> health -> stop -> update -> remove
with a per-app venv, scoped token, logs, and data preservation.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.request
import venv
from pathlib import Path
from typing import Any


class HostError(RuntimeError):
    pass


def _read_manifest(source: Path) -> dict[str, Any]:
    path = source / "manifest.json"
    if not path.is_file():
        raise HostError(f"manifest missing: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    for key in ("slug", "version", "package", "entry", "core_api", "app_api"):
        if not data.get(key):
            raise HostError(f"manifest missing {key}")
    return data


def _app_dir(home: Path, slug: str) -> Path:
    return home / "apps" / slug


def _data_dir(home: Path, slug: str) -> Path:
    return _app_dir(home, slug) / "data"


def _state_path(home: Path, slug: str) -> Path:
    return _app_dir(home, slug) / "state.json"


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _venv_python(venv_dir: Path) -> Path:
    candidates = (venv_dir / "bin" / "python", venv_dir / "Scripts" / "python.exe")
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise HostError(f"venv python not found: {venv_dir}")


def _ensure_venv(app_dir: Path) -> Path:
    venv_dir = app_dir / "venv"
    for candidate in (venv_dir / "bin" / "python", venv_dir / "Scripts" / "python.exe"):
        if candidate.is_file():
            return candidate
    venv.EnvBuilder(with_pip=False).create(venv_dir)
    return _venv_python(venv_dir)


def install(home: Path, source: Path) -> dict[str, Any]:
    manifest = _read_manifest(source)
    slug = str(manifest["slug"])
    app_dir = _app_dir(home, slug)
    data = _data_dir(home, slug)
    data.mkdir(parents=True, exist_ok=True)
    code = app_dir / "code"
    if code.exists():
        shutil.rmtree(code)
    shutil.copytree(source, code)
    _ensure_venv(app_dir)
    (app_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return {"slug": slug, "version": manifest["version"], "path": str(app_dir)}


def start(home: Path, slug: str) -> dict[str, Any]:
    app_dir = _app_dir(home, slug)
    manifest = json.loads((app_dir / "manifest.json").read_text(encoding="utf-8"))
    python = _ensure_venv(app_dir)
    port = int(manifest.get("port") or 0) or _free_port()
    token = os.urandom(24).hex()
    logs = home / "logs" / "apps" / slug
    logs.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env.update({
        "LOOMSCI_CORE_URL": "http://127.0.0.1:0",
        "LOOMSCI_APP_TOKEN": token,
        "LOOMSCI_APP_SLUG": slug,
        "LOOMSCI_APP_PORT": str(port),
        "LOOMSCI_APP_DATA_DIR": str(_data_dir(home, slug)),
        "LOOMSCI_APP_LOG_DIR": str(logs),
    })
    stdout = (logs / "stdout.log").open("ab")
    stderr = (logs / "stderr.log").open("ab")
    proc = subprocess.Popen(
        [str(python), "-m", f"{manifest['package']}.{manifest['entry']}"],
        cwd=app_dir / "code",
        env=env,
        stdout=stdout,
        stderr=stderr,
    )
    health = str(manifest.get("health") or "/health")
    url = f"http://127.0.0.1:{port}{health}"
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise HostError(f"app exited during startup: {proc.returncode}")
        try:
            with urllib.request.urlopen(url, timeout=0.5) as response:
                if response.status == 200:
                    state = {"pid": proc.pid, "port": port, "url": url}
                    (app_dir / "state.json").write_text(json.dumps(state), encoding="utf-8")
                    return state
        except Exception:
            time.sleep(0.25)
    stop(home, slug)
    raise HostError("app health timeout")


def stop(home: Path, slug: str) -> dict[str, Any]:
    state_path = _state_path(home, slug)
    if not state_path.is_file():
        return {"slug": slug, "stopped": False}
    state = json.loads(state_path.read_text(encoding="utf-8"))
    pid = int(state.get("pid") or 0)
    stopped = False
    if pid:
        try:
            os.kill(pid, signal.SIGTERM)
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                try:
                    os.kill(pid, 0)
                except OSError:
                    stopped = True
                    break
                time.sleep(0.1)
            if not stopped:
                os.kill(pid, signal.SIGKILL)
                stopped = True
        except OSError:
            stopped = True
    state_path.unlink(missing_ok=True)
    return {"slug": slug, "stopped": stopped}


def update(home: Path, source: Path) -> dict[str, Any]:
    manifest = _read_manifest(source)
    slug = str(manifest["slug"])
    stop(home, slug)
    app_dir = _app_dir(home, slug)
    backup = app_dir / "code.prev"
    if backup.exists():
        shutil.rmtree(backup)
    if (app_dir / "code").exists():
        shutil.move(str(app_dir / "code"), str(backup))
    install(home, source)
    return {"slug": slug, "version": manifest["version"], "updated": True}


def remove(home: Path, slug: str) -> dict[str, Any]:
    stop(home, slug)
    app_dir = _app_dir(home, slug)
    keep = _data_dir(home, slug)
    preserve = keep / ".preserve"
    preserve.mkdir(parents=True, exist_ok=True)
    for child in app_dir.iterdir():
        if child.name == "data":
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
    return {"slug": slug, "removed": True, "data": str(keep)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--home", default=str(Path.home() / ".loomsci-prototype"))
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("install", "update"):
        cmd = sub.add_parser(name)
        cmd.add_argument("source")
    for name in ("start", "stop", "remove"):
        cmd = sub.add_parser(name)
        cmd.add_argument("slug")
    args = parser.parse_args()
    home = Path(args.home).expanduser()
    home.mkdir(parents=True, exist_ok=True)
    if args.command == "install":
        result = install(home, Path(args.source).resolve())
    elif args.command == "update":
        result = update(home, Path(args.source).resolve())
    elif args.command == "start":
        result = start(home, args.slug)
    elif args.command == "stop":
        result = stop(home, args.slug)
    else:
        result = remove(home, args.slug)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
