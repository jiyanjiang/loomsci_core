#!/usr/bin/env python3
"""Exercise the minimal process contract on the current platform."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HOST = ROOT / "app_host" / "host.py"
APP = ROOT / "hello_app"


def run(*args: str) -> dict:
    result = subprocess.run(
        [sys.executable, str(HOST), *args],
        text=True,
        capture_output=True,
    )
    if result.returncode:
        raise SystemExit(f"host failed: {args}\n{result.stdout}\n{result.stderr}")
    return json.loads(result.stdout)


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp) / "home"
        source = Path(tmp) / "hello"
        shutil.copytree(APP, source)
        installed = run("--home", str(home), "install", str(source))
        print("installed", installed["slug"], installed["version"])
        started = run("--home", str(home), "start", "hello")
        with urllib.request.urlopen(started["url"], timeout=5) as response:
            health = json.loads(response.read())
        print("health", health)
        assert health["ok"] is True
        assert health["token_present"] is True
        stopped = run("--home", str(home), "stop", "hello")
        assert stopped["stopped"] is True
        manifest = json.loads((source / "manifest.json").read_text())
        manifest["version"] = "0.2.0"
        (source / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        updated = run("--home", str(home), "update", str(source))
        assert updated["version"] == "0.2.0"
        started = run("--home", str(home), "start", "hello")
        with urllib.request.urlopen(started["url"], timeout=5) as response:
            assert json.loads(response.read())["ok"] is True
        removed = run("--home", str(home), "remove", "hello")
        assert removed["removed"] is True
        assert Path(removed["data"]).is_dir()
        print("lifecycle ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
