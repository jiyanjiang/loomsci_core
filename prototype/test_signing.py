#!/usr/bin/env python3
"""Exercise the Ed25519 signing prototype on the current platform."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SIGN = ROOT / "signing" / "sign_manifest.py"


def run(*args: str) -> tuple[int, dict]:
    result = subprocess.run([sys.executable, str(SIGN), *args], text=True, capture_output=True)
    try:
        payload = json.loads(result.stdout.strip().splitlines()[-1])
    except Exception:
        payload = {"raw": result.stdout, "stderr": result.stderr}
    return result.returncode, payload


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        payload = root / "payload.bin"
        payload.write_bytes(b"hello signed world")
        manifest = root / "manifest.json"
        manifest.write_text(json.dumps({
            "kind": "app",
            "name": "hello",
            "version": "0.1.0",
            "platform": "any",
            "payload_sha256": hashlib.sha256(payload.read_bytes()).hexdigest(),
            "payload_bytes": payload.stat().st_size,
        }), encoding="utf-8")
        private, public, sig = root / "key.pem", root / "pub.pem", root / "manifest.sig"
        wrong_private, wrong_public = root / "wrong.pem", root / "wrong.pub"
        for args in (
            ("keygen", "--private", str(private), "--public", str(public)),
            ("keygen", "--private", str(wrong_private), "--public", str(wrong_public)),
            ("sign", "--manifest", str(manifest), "--key", str(private), "--out", str(sig)),
        ):
            code, out = run(*args)
            assert code == 0, (args, out)
        code, out = run("verify", "--manifest", str(manifest), "--sig", str(sig),
                        "--public", str(public), "--payload", str(payload))
        assert code == 0 and out["ok"], out
        print("valid signature: PASS")
        original = manifest.read_text(encoding="utf-8")
        tampered = json.loads(original)
        tampered["version"] = "0.1.1"
        manifest.write_text(json.dumps(tampered, sort_keys=True, separators=(",", ":")), encoding="utf-8")
        code, out = run("verify", "--manifest", str(manifest), "--sig", str(sig),
                        "--public", str(public), "--payload", str(payload))
        assert code != 0 and out["error"] == "signature_invalid", out
        manifest.write_text(original, encoding="utf-8")
        print("tampered manifest: PASS")
        payload.write_bytes(b"tampered")
        code, out = run("verify", "--manifest", str(manifest), "--sig", str(sig),
                        "--public", str(public), "--payload", str(payload))
        assert code != 0 and out["error"] == "payload_hash_mismatch", out
        print("tampered payload: PASS")
        payload.write_bytes(b"hello signed world")
        code, out = run("verify", "--manifest", str(manifest), "--sig", str(sig),
                        "--public", str(wrong_public), "--payload", str(payload))
        assert code != 0 and out["error"] == "signature_invalid", out
        print("wrong key: PASS")
    print("signing prototype: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
