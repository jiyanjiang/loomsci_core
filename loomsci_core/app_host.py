"""Minimal Core v0 App Host prototype."""

from __future__ import annotations

import json
import os
import secrets
import shutil
import socket
import subprocess
import time
import urllib.request
import venv
from pathlib import Path
from typing import Any


class AppHostError(RuntimeError):
    pass


class AppHost:
    def __init__(self, home: Path, core_url: str):
        self.home = home
        self.core_url = core_url.rstrip("/")
        self.tokens: dict[str, dict[str, Any]] = {}
        self.procs: dict[str, subprocess.Popen] = {}
        self.ports: dict[str, int] = {}

    def _dir(self, slug: str) -> Path:
        return self.home / "apps" / slug

    def _manifest(self, source: Path) -> dict[str, Any]:
        path = source / "manifest.json"
        if not path.is_file():
            raise AppHostError(f"manifest missing: {path}")
        data = json.loads(path.read_text(encoding="utf-8"))
        for key in ("slug", "version", "package", "entry", "health"):
            if not data.get(key):
                raise AppHostError(f"manifest missing {key}")
        return data

    def _venv_python(self, slug: str) -> Path:
        venv_dir = self._dir(slug) / "venv"
        candidates = (venv_dir / "bin" / "python", venv_dir / "Scripts" / "python.exe")
        for candidate in candidates:
            if candidate.is_file():
                return candidate
        venv.EnvBuilder(with_pip=False).create(venv_dir)
        for candidate in candidates:
            if candidate.is_file():
                return candidate
        raise AppHostError(f"venv python missing: {venv_dir}")

    def install(self, source: Path) -> dict[str, Any]:
        manifest = self._manifest(source)
        slug = str(manifest["slug"])
        target = self._dir(slug)
        data = target / "data"
        data.mkdir(parents=True, exist_ok=True)
        code = target / "code"
        if code.exists():
            shutil.rmtree(code)
        shutil.copytree(source, code)
        (target / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        self._venv_python(slug)
        from . import store
        conn = store.connect(self.home / "data" / "core.db")
        try:
            store.upsert_app(conn, slug=slug, version=str(manifest["version"]), manifest=manifest)
        finally:
            conn.close()
        return {"slug": slug, "version": manifest["version"]}

    def _free_port(self) -> int:
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            return int(sock.getsockname()[1])

    def start(self, slug: str) -> dict[str, Any]:
        if slug in self.procs and self.procs[slug].poll() is None:
            return {"slug": slug, "running": True, "port": self.ports[slug]}
        self.stop(slug)
        manifest_path = self._dir(slug) / "manifest.json"
        if not manifest_path.is_file():
            raise AppHostError(f"app not installed: {slug}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        python = self._venv_python(slug)
        port = self._free_port()
        token = secrets.token_hex(24)
        logs = self.home / "logs" / "apps" / slug
        logs.mkdir(parents=True, exist_ok=True)
        env = dict(os.environ)
        env.update({
            "LOOMSCI_CORE_URL": self.core_url,
            "LOOMSCI_APP_TOKEN": token,
            "LOOMSCI_APP_SLUG": slug,
            "LOOMSCI_APP_PORT": str(port),
            "LOOMSCI_APP_DATA_DIR": str(self._dir(slug) / "data"),
            "LOOMSCI_APP_LOG_DIR": str(logs),
        })
        stdout = (logs / "stdout.log").open("ab")
        stderr = (logs / "stderr.log").open("ab")
        proc = subprocess.Popen(
            [str(python), "-m", f"{manifest['package']}.{manifest['entry']}"],
            cwd=self._dir(slug) / "code",
            env=env,
            stdout=stdout,
            stderr=stderr,
        )
        stdout.close()
        stderr.close()
        url = f"http://127.0.0.1:{port}{manifest['health']}"
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                raise AppHostError(f"app exited during startup: {proc.returncode}")
            try:
                with urllib.request.urlopen(url, timeout=0.5) as response:
                    if response.status == 200:
                        self.procs[slug] = proc
                        self.ports[slug] = port
                        self.tokens[token] = {"slug": slug, "permissions": manifest.get("permissions", [])}
                        return {"slug": slug, "running": True, "port": port}
            except Exception:
                time.sleep(0.25)
        proc.terminate()
        raise AppHostError("app health timeout")

    def stop(self, slug: str) -> dict[str, Any]:
        proc = self.procs.pop(slug, None)
        self.ports.pop(slug, None)
        for token, info in list(self.tokens.items()):
            if info.get("slug") == slug:
                self.tokens.pop(token, None)
        if proc is None or proc.poll() is not None:
            return {"slug": slug, "stopped": False}
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        return {"slug": slug, "stopped": True}

    def update(self, slug: str, source: Path) -> dict[str, Any]:
        self.stop(slug)
        return self.install(source)

    def remove(self, slug: str) -> dict[str, Any]:
        self.stop(slug)
        target = self._dir(slug)
        if target.exists():
            for child in target.iterdir():
                if child.name == "data":
                    continue
                if child.is_dir():
                    shutil.rmtree(child)
                else:
                    child.unlink()
        from . import store
        conn = store.connect(self.home / "data" / "core.db")
        try:
            store.remove_app(conn, slug)
        finally:
            conn.close()
        return {"slug": slug, "removed": True, "data": str(target / "data")}
