#!/usr/bin/env python3
"""Exercise the data-only backup/restore prototype."""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKUP = ROOT / "backup_restore" / "backup.py"


def run(*args: str) -> tuple[int, dict]:
    result = subprocess.run([sys.executable, str(BACKUP), *args], text=True, capture_output=True)
    try:
        payload = json.loads(result.stdout.strip())
    except Exception:
        try:
            payload = json.loads(result.stdout.strip().splitlines()[-1])
        except Exception:
            payload = {"raw": result.stdout, "stderr": result.stderr}
    return result.returncode, payload


def make_home(home: Path) -> None:
    (home / "data" / "blobs").mkdir(parents=True)
    (home / "apps" / "report" / "data").mkdir(parents=True)
    (home / "apps" / "report" / "code").mkdir(parents=True)
    (home / "apps" / "report" / "venv").mkdir(parents=True)
    (home / "logs").mkdir()
    (home / "data" / "blobs" / "a.txt").write_text("blob", encoding="utf-8")
    (home / "apps" / "report" / "data" / "app.txt").write_text("app-data", encoding="utf-8")
    (home / "apps" / "installed.json").write_text('{"report":{"version":"0.1.0"}}', encoding="utf-8")
    (home / "local.token").write_text("old-token\n", encoding="utf-8")
    (home / "logs" / "core.log").write_text("log", encoding="utf-8")
    (home / "apps" / "report" / "code" / "server.py").write_text("code", encoding="utf-8")
    (home / "apps" / "report" / "venv" / "x").write_text("venv", encoding="utf-8")
    conn = sqlite3.connect(home / "data" / "core.db")
    conn.execute("CREATE TABLE items(id TEXT PRIMARY KEY, body TEXT)")
    conn.execute("INSERT INTO items VALUES('i-1','hello')")
    conn.commit()
    conn.close()


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        home = root / "home"
        make_home(home)
        backup = root / "backup"
        code, out = run("create", "--home", str(home), "--out", str(backup))
        assert code == 0, out
        code, out = run("verify", "--backup", str(backup))
        assert code == 0, out
        files = {item["path"] for item in out["files"]}
        assert "data/core.db" in files
        assert "data/blobs/a.txt" in files
        assert "apps/report/data/app.txt" in files
        assert not any("local.token" in path or "logs/" in path or "venv/" in path for path in files)
        print("backup and verify: PASS")
        restored = root / "restored"
        code, out = run("restore", "--backup", str(backup), "--home", str(restored))
        assert code == 0, out
        conn = sqlite3.connect(restored / "data" / "core.db")
        assert conn.execute("SELECT body FROM items").fetchone()[0] == "hello"
        conn.close()
        assert (restored / "data" / "blobs" / "a.txt").read_text() == "blob"
        assert (restored / "apps" / "report" / "data" / "app.txt").read_text() == "app-data"
        assert (restored / "local.token").read_text() != "old-token\n"
        assert not (restored / "apps" / "report" / "code").exists()
        print("restore data and token: PASS")
        nonempty = root / "nonempty"
        nonempty.mkdir()
        (nonempty / "marker").write_text("keep", encoding="utf-8")
        code, out = run("restore", "--backup", str(backup), "--home", str(nonempty))
        assert code != 0, out
        print("nonempty requires force: PASS")
        broken = root / "broken"
        import shutil
        shutil.copytree(backup, broken)
        (broken / "data" / "core.db").write_bytes(b"truncated")
        code, out = run("verify", "--backup", str(broken))
        assert code != 0, out
        target = root / "target"
        target.mkdir()
        (target / "marker").write_text("keep", encoding="utf-8")
        code, out = run("restore", "--backup", str(broken), "--home", str(target), "--force")
        assert code != 0, out
        assert (target / "marker").read_text() == "keep"
        print("truncated backup rejected: PASS")
        print("failed restore leaves target unchanged: PASS")
    print("backup/restore prototype: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
