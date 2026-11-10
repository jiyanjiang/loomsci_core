"""Start/stop installed add-on servers without importing add-on code.

Each add-on is a standalone process under ``packs/<package>/``. Runtime state
lives under ``runtime/addons/<name>.json``; logs under ``logs/addons/``.
"""

from __future__ import annotations

import ctypes
import http.client
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core import addons


class AddonRuntimeError(RuntimeError):
    pass


_PROCESSES: dict[str, subprocess.Popen] = {}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _state_path(home: Path, name: str) -> Path:
    return home / "runtime" / "addons" / f"{name}.json"


def _read_state(home: Path, name: str) -> dict[str, Any]:
    path = _state_path(home, name)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _write_state(home: Path, name: str, state: dict[str, Any]) -> None:
    path = _state_path(home, name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def _clear_state(home: Path, name: str) -> None:
    try:
        _state_path(home, name).unlink()
    except OSError:
        pass


def _alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(0x1000, False, pid)  # QUERY_LIMITED_INFORMATION
        if handle:
            kernel32.CloseHandle(handle)
            return True
        return kernel32.GetLastError() == 5  # access denied still means it exists
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _port_open(port: int) -> bool:
    if not port:
        return False
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.3)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def _health(port: int, path: str) -> bool:
    if not port:
        return False
    try:
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
        conn.request("GET", path or "/")
        response = conn.getresponse()
        status = response.status
        response.read()
        conn.close()
        return 200 <= status < 300
    except (OSError, http.client.HTTPException):
        return False


def _installed_manifest(home: Path, name: str) -> dict[str, Any]:
    destination = addons.target(home, name)
    path = destination / "manifest.json"
    if not path.is_file():
        raise AddonRuntimeError(f"add-on not installed: {name}")
    return addons.read_manifest(destination)


def _python(home: Path) -> str:
    candidates = (
        home / "venv" / "Scripts" / "python.exe",
        home / "venv" / "bin" / "python",
    )
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return sys.executable


def _port_pid_windows(port: int) -> int:
    script = f"(Get-NetTCPConnection -LocalPort {port} -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1).OwningProcess"
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True, text=True, timeout=5,
        )
        value = (result.stdout or "").strip()
        return int(value) if value.isdigit() else 0
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return 0


def _spawn_windows(python: str, module: str, home: Path, port: int, log, env: dict[str, str]) -> subprocess.Popen:
    """Detach from the SSH/PowerShell job so the server survives the caller."""
    base = [python, "-u", "-m", module, "--home", str(home), "--port", str(port)]
    last: OSError | None = None
    for flags in (0x00000008 | 0x00000200 | 0x01000000, 0x00000008 | 0x00000200):
        try:
            return subprocess.Popen(
                base, cwd=str(home), env=env, stdin=subprocess.DEVNULL,
                stdout=log, stderr=subprocess.STDOUT, creationflags=flags, close_fds=True,
            )
        except OSError as exc:
            last = exc
    raise AddonRuntimeError(f"detached start failed: {last}") from None


def start(home: Path, name: str, timeout: float = 8.0) -> dict[str, Any]:
    manifest = _installed_manifest(home, name)
    port = int(manifest.get("port") or 0)
    if not 1 <= port <= 65535:
        raise AddonRuntimeError(f"{name} has no runnable port")
    current = _read_state(home, name)
    pid = int(current.get("pid") or 0)
    if _alive(pid):
        return {**status(home, name), "already_running": True}
    if _port_open(port):
        raise AddonRuntimeError(f"{name} port {port} already in use")

    log_dir = home / "logs" / "addons"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{name}.log"
    log = log_path.open("ab")
    module = f"packs.{manifest['package']}.{manifest['entry']}"
    env = {
        **os.environ,
        "PYTHONPATH": str(home),
        "PYTHONIOENCODING": "utf-8",
        "LOOMSCI_HOME": str(home),
    }
    kwargs: dict[str, Any] = {}
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    else:
        kwargs["start_new_session"] = True
    try:
        if os.name == "nt":
            process: subprocess.Popen = _spawn_windows(
                _python(home), module, home, port, log, env
            )
        else:
            process = subprocess.Popen(
                [_python(home), "-u", "-m", module, "--home", str(home), "--port", str(port)],
                cwd=str(home),
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                **kwargs,
            )
    finally:
        log.close()
    pid = process.pid
    _PROCESSES[name] = process
    _write_state(home, name, {
        "name": name,
        "pid": pid,
        "port": port,
        "package": manifest["package"],
        "entry": manifest["entry"],
        "log": str(log_path),
        "started_at": _now(),
    })
    deadline = time.monotonic() + max(0.5, float(timeout))
    while time.monotonic() < deadline:
        if _health(port, str(manifest.get("health") or "/")):
            actual = _port_pid_windows(port) if os.name == "nt" else 0
            if actual and actual != pid:
                pid = actual
                state = _read_state(home, name)
                state["pid"] = pid
                _write_state(home, name, state)
            return {**status(home, name), "started": True}
        if os.name != "nt" and not _alive(pid):
            tail = _tail(log_path)
            _clear_state(home, name)
            raise AddonRuntimeError(f"{name} exited: {tail}")
        time.sleep(0.2)
    _terminate(home, name, pid, process)
    _PROCESSES.pop(name, None)
    _clear_state(home, name)
    raise AddonRuntimeError(
        f"{name} did not become healthy on port {port}: "
        f"pid={pid} alive={_alive(pid)} port_open={_port_open(port)} "
        f"python={_python(home)} log={_tail(log_path)}"
    )


def _tail(path: Path, limit: int = 1200) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return text[-limit:].strip()


def _terminate(home: Path, name: str, pid: int, process: subprocess.Popen | None = None) -> None:
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    else:
        try:
            os.killpg(pid, signal.SIGTERM)
        except (ProcessLookupError, PermissionError, OSError):
            try:
                os.kill(pid, signal.SIGTERM)
            except OSError:
                pass
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline and _alive(pid):
        if process is not None:
            process.poll()
        time.sleep(0.1)
    if _alive(pid):
        try:
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], check=False,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                os.killpg(pid, signal.SIGKILL)
        except OSError:
            pass
    if isinstance(process, subprocess.Popen):
        try:
            process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            pass


def stop(home: Path, name: str) -> dict[str, Any]:
    current = _read_state(home, name)
    pid = int(current.get("pid") or 0)
    if not pid or not _alive(pid):
        _clear_state(home, name)
        return {"name": name, "running": False, "stopped": False}
    process = _PROCESSES.pop(name, None)
    _terminate(home, name, pid, process)
    _clear_state(home, name)
    return {"name": name, "running": False, "stopped": True}


def status(home: Path, name: str) -> dict[str, Any]:
    current = _read_state(home, name)
    pid = int(current.get("pid") or 0)
    manifest: dict[str, Any] = {}
    try:
        manifest = _installed_manifest(home, name)
    except AddonRuntimeError:
        pass
    port = int(current.get("port") or manifest.get("port") or 0)
    alive = _alive(pid)
    healthy = alive and _health(port, str(manifest.get("health") or "/"))
    return {
        "name": name,
        "running": alive,
        "healthy": healthy,
        "pid": pid or None,
        "port": port or None,
        "state": "running" if healthy else ("degraded" if alive else ("port_foreign" if _port_open(port) else "stopped")),
        "log": current.get("log"),
    }


def status_all(home: Path) -> list[dict[str, Any]]:
    return [status(home, name) for name in addons.installed(home)]


def start_all(home: Path) -> list[dict[str, Any]]:
    results = []
    for name in addons.installed(home):
        try:
            results.append(start(home, name))
        except AddonRuntimeError as exc:
            results.append({"name": name, "ok": False, "error": str(exc)})
    return results


def stop_all(home: Path) -> list[dict[str, Any]]:
    return [stop(home, name) for name in addons.installed(home)]
