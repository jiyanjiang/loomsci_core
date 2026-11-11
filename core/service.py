"""Login-time service installation for macOS and Windows.

The service starts the normal user-facing command:

    loomsci --home <home> up --detach

It is intentionally a login item, not a silent resident daemon: the detached
Core owns the process lifetime, and the same state/PID files are used.
"""

from __future__ import annotations

import os
import platform
import plistlib
import subprocess
from pathlib import Path
from typing import Any

LABEL = "com.loomsci.core"
TASK_NAME = "LoomSciCore"


class ServiceError(RuntimeError):
    pass


def _launcher(home: Path) -> Path:
    return home / "bin" / ("loomsci.cmd" if os.name == "nt" else "loomsci")


def _uid() -> str:
    try:
        return str(os.getuid())
    except AttributeError:
        return "0"


def plist_path(home: str | Path) -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"


def windows_wrapper(home: str | Path) -> Path:
    return Path(home).expanduser() / "runtime" / "service-start.cmd"


def windows_startup(home: str | Path) -> Path:
    appdata = os.environ.get("APPDATA")
    base = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
    return base / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / "LoomSciCore.cmd"


def _require_launcher(home: Path) -> Path:
    launcher = _launcher(home)
    if not launcher.is_file():
        raise ServiceError(f"launcher not found: {launcher}")
    return launcher


def _run(command: list[str], *, check: bool = False) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            command, capture_output=True, text=True, timeout=20, check=check
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ServiceError(str(exc)) from None


def _plist_payload(home: Path) -> dict[str, Any]:
    launcher = _require_launcher(home)
    logs = home / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    return {
        "Label": LABEL,
        "ProgramArguments": [
            str(launcher), "--home", str(home), "up", "--detach",
        ],
        "RunAtLoad": True,
        "KeepAlive": False,
        "WorkingDirectory": str(home),
        "StandardOutPath": str(logs / "service.out"),
        "StandardErrorPath": str(logs / "service.err"),
        "ProcessType": "Background",
    }


def _write_plist(home: Path) -> Path:
    path = plist_path(home)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = _plist_payload(home)
    tmp = path.with_suffix(".tmp")
    tmp.write_bytes(plistlib.dumps(payload))
    os.replace(tmp, path)
    return path


def _write_wrapper(home: Path) -> Path:
    _require_launcher(home)
    wrapper = windows_wrapper(home)
    wrapper.parent.mkdir(parents=True, exist_ok=True)
    log = home / "logs" / "service.log"
    python = home / "venv" / "Scripts" / "python.exe"
    if not python.is_file():
        python = home / "venv" / "Scripts" / "python"
    lines = [
        "@echo off",
        f'set "PYTHONPATH={home / "core"}"',
        'set "PYTHONSAFEPATH=1"',
        f'set "LOOMSCI_HOME={home}"',
        f'cd /d "{home}"',
        f'"{python}" -m cli.loomsci --home "{home}" up --detach >> "{log}" 2>&1',
    ]
    wrapper.write_bytes(("\r\n".join(lines) + "\r\n").encode("ascii"))
    return wrapper


def install(home: str | Path) -> dict[str, Any]:
    home = Path(home).expanduser()
    system = platform.system()
    if system == "Darwin":
        path = _write_plist(home)
        domain = f"gui/{_uid()}"
        _run(["launchctl", "bootout", domain, str(path)])
        result = _run(["launchctl", "bootstrap", domain, str(path)])
        if result.returncode != 0:
            fallback = _run(["launchctl", "load", "-w", str(path)])
            if fallback.returncode != 0:
                raise ServiceError(
                    (result.stderr or fallback.stderr or "launchctl bootstrap failed").strip()
                )
        return {"ok": True, "installed": True, "platform": system, "path": str(path)}
    if system == "Windows":
        wrapper = _write_wrapper(home)
        startup = windows_startup(home)
        startup.parent.mkdir(parents=True, exist_ok=True)
        startup.write_bytes(wrapper.read_bytes())
        # Remove a legacy scheduled task, if any.
        _run(["schtasks", "/Delete", "/TN", TASK_NAME, "/F"])
        return {"ok": True, "installed": True, "platform": system, "path": str(startup)}
    raise ServiceError(f"service install is not supported on {system}")


def uninstall(home: str | Path) -> dict[str, Any]:
    home = Path(home).expanduser()
    system = platform.system()
    if system == "Darwin":
        path = plist_path(home)
        domain = f"gui/{_uid()}"
        _run(["launchctl", "bootout", domain, str(path)])
        _run(["launchctl", "unload", "-w", str(path)])
        try:
            path.unlink()
        except OSError:
            pass
        return {"ok": True, "uninstalled": True, "platform": system}
    if system == "Windows":
        _run(["schtasks", "/Delete", "/TN", TASK_NAME, "/F"])
        for path in (windows_startup(home), windows_wrapper(home)):
            try:
                path.unlink()
            except OSError:
                pass
        return {"ok": True, "uninstalled": True, "platform": system}
    raise ServiceError(f"service uninstall is not supported on {system}")


def status(home: str | Path) -> dict[str, Any]:
    home = Path(home).expanduser()
    system = platform.system()
    if system == "Darwin":
        path = plist_path(home)
        result = _run(["launchctl", "print", f"gui/{_uid()}/{LABEL}"])
        return {
            "ok": True,
            "platform": system,
            "installed": path.is_file(),
            "loaded": result.returncode == 0,
            "path": str(path),
        }
    if system == "Windows":
        startup = windows_startup(home)
        return {
            "ok": True,
            "platform": system,
            "installed": startup.is_file(),
            "loaded": startup.is_file(),
            "path": str(startup),
        }
    return {"ok": False, "platform": system, "installed": False, "loaded": False}
