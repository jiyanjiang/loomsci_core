"""Detached Core lifecycle: start, status, stop, and primary UI URL."""

from __future__ import annotations

import http.client
import json
import os
import signal
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core import addon_runtime

STATE_NAME = "core.json"
PID_NAME = "core.pid"

_PROCESSES: dict[str, subprocess.Popen] = {}


class CoreRuntimeError(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _state_path(home: Path) -> Path:
    return home / "runtime" / STATE_NAME


def _pid_path(home: Path) -> Path:
    return home / "runtime" / PID_NAME


def _read_state(home: Path) -> dict[str, Any]:
    try:
        data = json.loads(_state_path(home).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    if not data:
        try:
            pid = int(_pid_path(home).read_text(encoding="ascii").strip())
        except (OSError, ValueError):
            pid = 0
        if pid:
            data = {"pid": pid}
    return data if isinstance(data, dict) else {}


def _write_state(home: Path, state: dict[str, Any]) -> None:
    path = _state_path(home)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    _pid_path(home).write_text(str(int(state.get("pid") or 0)), encoding="ascii")


def _clear_state(home: Path) -> None:
    for path in (_state_path(home), _pid_path(home)):
        try:
            path.unlink()
        except OSError:
            pass


def _alive(pid: int) -> bool:
    return addon_runtime._alive(pid)


def _port_open(host: str, port: int) -> bool:
    if not port:
        return False
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    with socket.socket(family, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.3)
        return sock.connect_ex((host, port)) == 0


def _health(host: str, port: int) -> dict[str, Any] | None:
    try:
        conn = http.client.HTTPConnection(host, port, timeout=2)
        conn.request("GET", "/v1/health")
        response = conn.getresponse()
        raw = response.read()
        conn.close()
        if not 200 <= response.status < 300:
            return None
        data = json.loads(raw or b"{}")
        return data if isinstance(data, dict) else None
    except (OSError, ValueError, http.client.HTTPException):
        return None


def _python(home: Path) -> str:
    for candidate in (
        home / "venv" / "Scripts" / "python.exe",
        home / "venv" / "bin" / "python",
    ):
        if candidate.is_file():
            return str(candidate)
    return sys.executable


def _python_path(home: Path) -> Path:
    installed = home / "core"
    if (installed / "cli" / "loomsci.py").is_file():
        return installed
    return Path(__file__).resolve().parents[1]


def _port_pid_windows(port: int) -> int:
    return addon_runtime._port_pid_windows(port)


def _terminate(
    home: Path, pid: int, process: subprocess.Popen | None = None
) -> None:
    addon_runtime._terminate(home, "core", pid, process)


def status(home: str | Path) -> dict[str, Any]:
    home = Path(home).expanduser()
    state = _read_state(home)
    pid = int(state.get("pid") or 0)
    host = str(state.get("host") or "127.0.0.1")
    port = int(state.get("port") or 0)
    running = bool(pid and _alive(pid))
    health = _health(host, port) if running and port else None
    return {
        "ok": running and health is not None,
        "running": running,
        "pid": pid,
        "host": host,
        "port": port,
        "health": health,
        "log": state.get("log"),
        "started_at": state.get("started_at"),
    }


def start(
    home: str | Path,
    *,
    host: str = "127.0.0.1",
    port: int = 8787,
    python_path: str | Path | None = None,
    timeout: float = 20.0,
) -> dict[str, Any]:
    home = Path(home).expanduser()
    current = status(home)
    if current["running"] and current["health"]:
        return {**current, "already_running": True}
    if _port_open(host, port):
        raise CoreRuntimeError(f"port {host}:{port} is already in use")
    log_dir = home / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "core.log"
    log = log_path.open("ab")
    root = Path(python_path).expanduser() if python_path else _python_path(home)
    command = [
        _python(home),
        "-m",
        "cli.loomsci",
        "serve",
        "--host",
        host,
        "--port",
        str(port),
    ]
    env = {
        **os.environ,
        "PYTHONPATH": str(root),
        "PYTHONIOENCODING": "utf-8",
        "LOOMSCI_HOME": str(home),
    }
    try:
        if os.name == "nt":
            process = addon_runtime._spawn_windows(command, home, log, env)
        else:
            process = subprocess.Popen(
                command,
                cwd=str(home),
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
    except OSError as exc:
        log.close()
        raise CoreRuntimeError(f"failed to start Core: {exc}") from None
    finally:
        try:
            log.close()
        except OSError:
            pass
    pid = process.pid
    _PROCESSES[str(home)] = process
    _write_state(home, {
        "pid": pid,
        "host": host,
        "port": port,
        "log": str(log_path),
        "started_at": _now(),
    })
    deadline = time.monotonic() + max(1.0, float(timeout))
    while time.monotonic() < deadline:
        if _health(host, port):
            if os.name == "nt":
                actual = _port_pid_windows(port)
                if actual and actual != pid:
                    pid = actual
                    _write_state(home, {
                        "pid": pid, "host": host, "port": port,
                        "log": str(log_path), "started_at": _now(),
                    })
            result = status(home)
            result["started"] = True
            return result
        if not _alive(pid):
            break
        time.sleep(0.2)
    _terminate(home, pid, process)
    _PROCESSES.pop(str(home), None)
    _clear_state(home)
    tail = ""
    try:
        tail = log_path.read_text(encoding="utf-8", errors="replace")[-1000:].strip()
    except OSError:
        pass
    raise CoreRuntimeError(
        f"Core did not become healthy on {host}:{port}; log={log_path}\n{tail}"
    )


def stop(home: str | Path) -> dict[str, Any]:
    home = Path(home).expanduser()
    state = _read_state(home)
    pid = int(state.get("pid") or 0)
    process = _PROCESSES.pop(str(home), None)
    if pid:
        _terminate(home, pid, process)
    _clear_state(home)
    result = status(home)
    return {**result, "stopped": True}


def primary_url(home: str | Path, *, core_port: int = 8787) -> str:
    home = Path(home).expanduser()
    try:
        for item in addon_runtime.status_all(home):
            if item.get("name") == "ui-shell" and item.get("running") and item.get("port"):
                return f"http://127.0.0.1:{int(item['port'])}/app/posts"
    except Exception:  # noqa: BLE001 - UI choice must not block Core
        pass
    return f"http://127.0.0.1:{int(core_port)}/app/posts"
