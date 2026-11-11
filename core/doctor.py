"""Diagnostics for an installed Loomsci home."""

from __future__ import annotations

import http.client
import importlib.util
import json
import os
import shutil
import sqlite3
from pathlib import Path
from typing import Any

from core import addon_runtime, addons


def _core_health(port: int) -> dict[str, Any]:
    try:
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
        conn.request("GET", "/v1/health")
        response = conn.getresponse()
        data = json.loads(response.read().decode("utf-8"))
        conn.close()
        return {"ok": 200 <= response.status < 300, "status": response.status, "data": data}
    except Exception as exc:  # noqa: BLE001 - diagnostic boundary
        return {"ok": False, "error": type(exc).__name__}


def _db_check(home: Path) -> dict[str, Any]:
    db = home / "data" / "data.db"
    if not db.is_file():
        return {"ok": False, "error": "database not found"}
    conn = None
    try:
        conn = sqlite3.connect(f"file:{db.resolve().as_posix()}?mode=ro", uri=True)
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        counts = {}
        for table in ("posts", "tasks", "facts", "attachments"):
            try:
                counts[table] = int(conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0])
            except sqlite3.Error:
                counts[table] = 0
        return {"ok": integrity == "ok", "integrity": integrity, "counts": counts}
    except sqlite3.Error as exc:
        return {"ok": False, "error": str(exc)}
    finally:
        if conn is not None:
            conn.close()


def ides() -> dict[str, dict[str, Any]]:
    candidates = {
        "workbuddy": [Path("/Applications/WorkBuddy.app"), shutil.which("workbuddy")],
        "opencode": [shutil.which("opencode")],
        "omp": [shutil.which("omp")],
        "qoder": [Path("/Applications/Qoder.app"), shutil.which("qoder")],
        "cursor": [Path("/Applications/Cursor.app"), shutil.which("cursor")],
        "codebuddy": [Path("/Applications/CodeBuddy.app"), shutil.which("codebuddy")],
    }
    local = os.environ.get("LOCALAPPDATA")
    if local:
        base = Path(local)
        candidates["workbuddy"].append(base / "Programs" / "WorkBuddy" / "WorkBuddy.exe")
        candidates["cursor"].append(base / "Programs" / "Cursor" / "Cursor.exe")
    result = {}
    for name, paths in candidates.items():
        found = next((str(path) for path in paths if path and Path(path).exists()), None)
        result[name] = {"found": bool(found), "path": found}
    return result


def _config_check(home: Path) -> dict[str, Any]:
    from core import llm_config

    configured = bool(llm_config.get_key(home, "deepseek"))
    return {
        "ok": True,
        "deepseek_configured": configured,
        "providers": {name: llm_config.public(home, name) for name in ("deepseek",)},
    }


def run(home: str | Path, *, port: int = 8787) -> dict[str, Any]:
    home = Path(home).expanduser()
    checks: dict[str, Any] = {}
    checks["home"] = {"ok": home.is_dir(), "path": str(home)}
    checks["database"] = _db_check(home)
    checks["core"] = _core_health(port)
    installed = addons.installed(home)
    checks["addons"] = {
        "installed": installed,
        "states": addon_runtime.status_all(home) if installed else [],
    }
    checks["ides"] = ides()
    checks["tools"] = {
        "ffmpeg": bool(shutil.which("ffmpeg")),
        "rapidocr": importlib.util.find_spec("rapidocr_onnxruntime") is not None,
        "faster_whisper": importlib.util.find_spec("faster_whisper") is not None,
    }
    checks["config"] = _config_check(home)
    checks["disk"] = {"free_bytes": shutil.disk_usage(home).free} if home.exists() else {"free_bytes": 0}
    critical = [checks["home"]["ok"], checks["database"]["ok"]]
    warnings = []
    if not checks["core"]["ok"]:
        warnings.append("core is not reachable on the configured port")
    if not installed:
        warnings.append("no add-ons installed")
    for item in checks["addons"]["states"]:
        if item.get("state") != "running":
            warnings.append(f"add-on {item['name']} is {item.get('state')}")
    if not checks["tools"]["ffmpeg"]:
        warnings.append("ffmpeg not found; media previews/transforms unavailable")
    if not any(item["found"] for item in checks["ides"].values()):
        warnings.append("no AI IDE detected; install WorkBuddy, opencode, omp, or Qoder")
    if not checks["config"]["deepseek_configured"]:
        warnings.append("DeepSeek API key not configured")
    return {
        "ok": all(critical),
        "home": str(home),
        "checks": checks,
        "warnings": warnings,
    }
