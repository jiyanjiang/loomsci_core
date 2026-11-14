#!/usr/bin/env python3
"""M1 end-to-end acceptance: Core + App + backup + restore + migration."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CLI = ROOT / "core_v0" / "cli.py"
BACKUP = ROOT / "core_v0" / "backup.py"
DEMO = ROOT / "core_v0" / "demo_app"
sys.path.insert(0, str(ROOT / "core_v0"))
import backup as backup_store  # noqa: E402


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def run(*args: str) -> tuple[int, dict]:
    result = subprocess.run([sys.executable, str(CLI), *args], text=True, capture_output=True)
    try:
        payload = json.loads(result.stdout.strip())
    except Exception:
        payload = {"raw": result.stdout, "stderr": result.stderr}
    return result.returncode, payload


def request(port: int, token: str, method: str, path: str, body: dict | None = None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}", data=data, method=method,
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=15) as response:
        return response.status, json.loads(response.read())


def main() -> int:
    migrated = Path(os.environ["MIGRATED_HOME"]) if os.environ.get("MIGRATED_HOME") else None
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp) / "home"
        port = free_port()
        code, out = run("--home", str(home), "--port", str(port), "start", "--json")
        assert code == 0, out
        token = (home / "local.token").read_text(encoding="utf-8").strip()
        try:
            status, item = request(port, token, "POST", "/v1/items", {
                "app": "report", "type": "report.note", "title": "M1",
                "body": "acceptance", "tags": ["m1"],
            })
            assert status == 201, item
            item_id = item["item"]["id"]
            status, blob = request(port, token, "POST", "/v1/blobs", {
                "filename": "m1.md", "content_type": "text/markdown",
                "content_base64": "IyBtMQ==", "item_id": item_id,
            })
            assert status == 201, blob
            status, _ = request(port, token, "POST", "/v1/apps/install", {"source": str(DEMO)})
            assert status == 201, _
            status, started = request(port, token, "POST", "/v1/apps/demo/start", {})
            assert status == 200, started
            app_port = started["port"]
            with urllib.request.urlopen(f"http://127.0.0.1:{app_port}/write", data=b"{}", timeout=10) as response:
                assert response.status == 201
            status, _ = request(port, token, "POST", "/v1/apps/demo/stop", {})
            assert status == 200
            marker = home / "apps" / "demo" / "data" / "marker.txt"
            marker.write_text("keep", encoding="utf-8")
            status, created = request(port, token, "POST", "/v1/backups", {})
            assert status == 201, created
            backup_path = Path(created["backup"]["path"])
            code, out = run("--home", str(home), "stop", "--json")
            assert code == 0, out
            restored = Path(tmp) / "restored"
            backup_store.restore(backup_path, restored)
            port2 = free_port()
            code, out = run("--home", str(restored), "--port", str(port2), "start", "--json")
            assert code == 0, out
            token2 = (restored / "local.token").read_text(encoding="utf-8").strip()
            status, rows = request(port2, token2, "GET", "/v1/items?app=report")
            assert status == 200 and len(rows["items"]) == 1
            assert (restored / "apps" / "demo" / "data" / "marker.txt").read_text() == "keep"
            status, search = request(port2, token2, "GET", "/v1/search?q=acceptance")
            assert status == 200 and len(search["items"]) == 1
            run("--home", str(restored), "stop", "--json")
            print("core + app + backup + restore: PASS")
        finally:
            run("--home", str(home), "stop", "--json")

        if migrated and migrated.is_dir():
            port3 = free_port()
            code, out = run("--home", str(migrated), "--port", str(port3), "start", "--json")
            assert code == 0, out
            token3 = (migrated / "local.token").read_text(encoding="utf-8").strip()
            status, rows = request(port3, token3, "GET", "/v1/items?limit=200")
            assert status == 200 and rows["items"]
            print(f"migrated workspace: PASS ({len(rows['items'])} items)")
            run("--home", str(migrated), "stop", "--json")
        else:
            print("migrated workspace: SKIP (MIGRATED_HOME unset)")
    print("M1 acceptance: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
