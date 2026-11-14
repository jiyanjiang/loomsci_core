#!/usr/bin/env python3
"""Minimal Core v0 lifecycle CLI prototype."""

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
SERVER = ROOT / "server.py"


def state_path(home: Path) -> Path:
    return home / "runtime" / "core.json"


def _health(port: int, timeout: float = 1.0) -> dict | None:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/v1/health", timeout=timeout) as response:
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
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
    else:
        kwargs["start_new_session"] = True
    proc = subprocess.Popen(
        [sys.executable, str(SERVER), "--home", str(home), "--port", str(port)],
        cwd=ROOT,
        stdout=stdout,
        stderr=stderr,
        **kwargs,
    )
    stdout.close(); stderr.close()
    deadline = time.monotonic() + 20
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
    raise SystemExit("health_timeout")


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
    for name in ("start", "stop", "status", "doctor"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--json", action="store_true", default=argparse.SUPPRESS)
    args = parser.parse_args()
    home = Path(args.home)
    if args.command == "start":
        result = start(home, args.port)
    elif args.command == "stop":
        result = stop(home)
    else:
        result = status(home)
        if args.command == "doctor":
            token = home / "local.token"
            result["token_exists"] = token.is_file()
            result["token_mode"] = oct(token.stat().st_mode & 0o777) if token.is_file() else None
            result["db_exists"] = (home / "data" / "core.db").is_file()
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
