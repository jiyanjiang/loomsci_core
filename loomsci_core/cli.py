#!/usr/bin/env python3
"""Minimal Core v0 lifecycle CLI."""

from __future__ import annotations

import argparse
import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def state_path(home: Path) -> Path:
    return home / "runtime" / "core.json"


def _health(port: int, timeout: float = 1.0) -> dict | None:
    try:
        with _OPENER.open(f"http://127.0.0.1:{port}/v1/health", timeout=timeout) as response:
            return json.loads(response.read())
    except Exception:
        return None


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _read(home: Path) -> dict:
    path = state_path(home)
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write(home: Path, data: dict) -> None:
    path = state_path(home)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _clear(home: Path) -> None:
    state_path(home).unlink(missing_ok=True)


def _port_free(port: int) -> bool:
    with socket.socket() as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def start(home: Path, port: int) -> dict:
    home = home.expanduser()
    current = _read(home)
    if current:
        health = _health(int(current.get("port") or 0))
        if health:
            return {"ok": True, "already_running": True, **current}
        _clear(home)
    if not _port_free(port):
        raise SystemExit(f"port_in_use: {port}")
    logs = home / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    stdout = (logs / "core.stdout.log").open("ab")
    stderr = (logs / "core.stderr.log").open("ab")
    kwargs = {}
    if os.name == "nt":
        flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
        flags |= getattr(subprocess, "CREATE_BREAKAWAY_FROM_JOB", 0)
        kwargs["creationflags"] = flags
    else:
        kwargs["start_new_session"] = True
    proc = subprocess.Popen(
        [sys.executable, "-m", "loomsci_core.server", "--home", str(home), "--port", str(port)],
        cwd=ROOT.parent,
        stdout=stdout,
        stderr=stderr,
        **kwargs,
    )
    stdout.close(); stderr.close()
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise SystemExit(f"core_exited: {proc.returncode}")
        health = _health(port)
        if health:
            data = {"pid": proc.pid, "port": port, "url": f"http://127.0.0.1:{port}",
                    "home": str(home), "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
            _write(home, data)
            return {"ok": True, **data}
        time.sleep(0.25)
    proc.terminate()
    log = home / "logs" / "core.stderr.log"
    detail = log.read_text(encoding="utf-8", errors="replace") if log.is_file() else ""
    raise SystemExit("health_timeout\n" + detail)


def stop(home: Path) -> dict:
    data = _read(home)
    if not data:
        return {"ok": True, "stopped": False}
    pid = int(data.get("pid") or 0)
    stopped = False
    if pid:
        try:
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(pid), "/F"], stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, check=False)
                stopped = True
            else:
                os.kill(pid, signal.SIGTERM)
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    if not _pid_alive(pid):
                        stopped = True
                        break
                    time.sleep(0.1)
                if not stopped:
                    os.kill(pid, signal.SIGKILL)
                    stopped = True
        except OSError:
            stopped = True
    _clear(home)
    return {"ok": True, "stopped": stopped, "pid": pid}


def status(home: Path) -> dict:
    data = _read(home)
    if not data:
        return {"ok": True, "running": False}
    health = _health(int(data.get("port") or 0))
    return {"ok": True, "running": bool(health), "health": health, **data}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--home", default=str(Path.home() / ".loomsci-core-v0"))
    parser.add_argument("--port", type=int, default=8795)
    parser.add_argument("--json", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("start", "stop", "status"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--json", action="store_true", default=argparse.SUPPRESS)
    update_parser = sub.add_parser("update")
    update_sub = update_parser.add_subparsers(dest="update_command", required=True)
    check_cmd = update_sub.add_parser("check")
    check_cmd.add_argument("manifest", nargs="?")
    download_cmd = update_sub.add_parser("download")
    download_cmd.add_argument("manifest", nargs="?")
    update_sub.add_parser("status")
    update_sub.add_parser("install")
    apply_cmd = update_sub.add_parser("apply")
    apply_cmd.add_argument("manifest")
    apply_cmd.add_argument("--package", required=True)
    settings_cmd = update_sub.add_parser("settings")
    settings_cmd.add_argument("--enabled", choices=("on", "off"))
    settings_cmd.add_argument("--mode", choices=("notify", "download"))
    settings_cmd.add_argument("--channel")
    settings_cmd.add_argument("--manifest-url")
    args = parser.parse_args()
    home = Path(args.home)
    if args.command == "start":
        result = start(home, args.port)
    elif args.command == "stop":
        result = stop(home)
    elif args.command == "update":
        from . import update
        if args.update_command == "status":
            result = update.status(home)
        elif args.update_command == "check":
            result = update.check(home, args.manifest)
        elif args.update_command == "download":
            if args.manifest:
                checked = update.check(home, args.manifest)
                result = update.download(home) if checked.get("ok") else checked
            else:
                result = update.download(home)
        elif args.update_command == "install":
            result = update.apply_pending(home, args.port)
        elif args.update_command == "settings":
            changes = {}
            if args.enabled is not None:
                changes["enabled"] = args.enabled == "on"
            if args.mode is not None:
                changes["mode"] = args.mode
            if args.channel is not None:
                changes["channel"] = args.channel
            if args.manifest_url is not None:
                changes["manifest_url"] = args.manifest_url
            result = update.settings(home, **changes)
        else:
            manifest = update.load_manifest(args.manifest)
            result = update.apply_package(
                Path(args.package).expanduser(), manifest, home=home, port=args.port
            )
    else:
        result = status(home)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
