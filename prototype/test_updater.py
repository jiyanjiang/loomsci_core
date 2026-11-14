#!/usr/bin/env python3
"""Test the signed updater prototype on the current platform."""

from __future__ import annotations

import hashlib
import json
import shutil
import socket
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
UPDATER = ROOT / "updater" / "updater.py"
TRUST = ROOT / "signing" / "trust.py"
CLI = ROOT / "core_v0" / "cli.py"


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def run(*args: str) -> tuple[int, str]:
    result = subprocess.run(args, text=True, capture_output=True)
    return result.returncode, result.stdout + result.stderr


def trust_tool(*args: str) -> dict:
    code, out = run(sys.executable, str(TRUST), *args)
    if code != 0:
        raise SystemExit(out)
    return json.loads(out.strip().splitlines()[-1])


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        trust = root / "trust"; trust.mkdir()
        root_key, root_pub = root / "root.key", root / "root.pub"
        release_key, release_pub = root / "release.key", root / "release.pub"
        trust_tool("keygen", "--private", str(root_key), "--public", str(root_pub))
        trust_tool("keygen", "--private", str(release_key), "--public", str(release_pub))
        cert = root / "release.cert"
        trust_tool("certify", "--root-key", str(root_key), "--public", str(release_pub),
                   "--role", "release", "--out", str(cert))
        shutil.copy2(root_pub, trust / "root.pub")
        shutil.copy2(cert, trust / "release.cert")
        key_id = json.loads(cert.read_text())["key_id"]
        package = root / "package"; package.mkdir()
        payload = package / "payload.bin"; payload.write_text("new", encoding="utf-8")
        manifest = package / "manifest.json"
        manifest.write_text(json.dumps({
            "kind": "core", "name": "test", "version": "0.2.0", "platform": "any",
            "key_id": key_id,
            "payload_sha256": hashlib.sha256(payload.read_bytes()).hexdigest(),
            "payload_bytes": payload.stat().st_size,
        }, sort_keys=True, separators=(",", ":")), encoding="utf-8")
        sig = package / "manifest.sig"
        trust_tool("sign", "--manifest", str(manifest), "--key", str(release_key), "--out", str(sig))
        home = root / "home"; home.mkdir()
        (home / "core.current").write_text("old", encoding="utf-8")
        port = free_port()
        code, out = run(sys.executable, str(CLI), "--home", str(home), "--port", str(port), "start", "--json")
        assert code == 0, out
        code, out = run(sys.executable, str(UPDATER), "--package", str(package),
                        "--home", str(home), "--trust", str(trust), "--port", str(port))
        assert code == 0, out
        assert (home / "core.current").read_text() == "new"
        assert (home / "core.previous").read_text() == "old"
        assert list((home / "backups").glob("backup-*"))
        print("signed update: PASS")
        bad = root / "bad"; shutil.copytree(package, bad)
        (bad / "payload.bin").write_text("tampered", encoding="utf-8")
        code, out = run(sys.executable, str(UPDATER), "--package", str(bad),
                        "--home", str(home), "--trust", str(trust), "--port", str(port))
        assert code != 0, out
        assert (home / "core.current").read_text() == "new"
        print("tampered package rejected: PASS")
        run(sys.executable, str(CLI), "--home", str(home), "stop", "--json")
    print("updater prototype: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
