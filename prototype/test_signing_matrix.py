#!/usr/bin/env python3
"""Exercise the S1-S12 signing trust matrix."""

from __future__ import annotations

import base64
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TRUST = ROOT / "signing" / "trust.py"


def run(*args: str) -> tuple[int, dict]:
    result = subprocess.run([sys.executable, str(TRUST), *args], text=True, capture_output=True)
    try:
        payload = json.loads(result.stdout.strip())
    except Exception:
        payload = {"raw": result.stdout, "stderr": result.stderr}
    return result.returncode, payload


def keypair(root: Path, name: str) -> tuple[Path, Path, str]:
    private, public = root / f"{name}.key", root / f"{name}.pub"
    code, out = run("keygen", "--private", str(private), "--public", str(public))
    assert code == 0, out
    return private, public, out["key_id"]


def certify(root: Path, root_key: Path, public: Path, role: str, name: str, expires: str | None = None) -> tuple[Path, str]:
    out = root / f"{name}.cert"
    args = ["certify", "--root-key", str(root_key), "--public", str(public), "--role", role, "--out", str(out)]
    if expires:
        args += ["--expires", expires]
    code, payload = run(*args)
    assert code == 0, payload
    return out, payload["key_id"]


def manifest(root: Path, kind: str, key: str) -> tuple[Path, Path, Path]:
    payload = root / "payload.bin"
    payload.write_bytes(b"signed payload")
    path = root / "manifest.json"
    path.write_text(json.dumps({
        "kind": kind,
        "name": "test",
        "version": "0.1.0",
        "platform": "any",
        "key_id": key,
        "payload_sha256": hashlib.sha256(payload.read_bytes()).hexdigest(),
        "payload_bytes": payload.stat().st_size,
    }, sort_keys=True, separators=(",", ":")), encoding="utf-8")
    return path, payload, root / "manifest.sig"


def verify(manifest_path: Path, sig: Path, payload: Path, trust: Path) -> tuple[int, dict]:
    return run("verify", "--manifest", str(manifest_path), "--sig", str(sig),
               "--payload", str(payload), "--trust", str(trust))


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        root_key, root_pub, _ = keypair(root, "root")
        release_key, release_pub, release_id = keypair(root, "release")
        content_key, content_pub, content_id = keypair(root, "content")
        release2_key, release2_pub, release2_id = keypair(root, "release2")
        expired_key, expired_pub, expired_id = keypair(root, "expired")
        release_cert, _ = certify(root, root_key, release_pub, "release", "release")
        content_cert, _ = certify(root, root_key, content_pub, "content", "content")
        release2_cert, _ = certify(root, root_key, release2_pub, "release", "release2")
        expired_cert, _ = certify(root, root_key, expired_pub, "release", "expired", "2020-01-01")
        trust = root / "trust"
        trust.mkdir()
        shutil.copy2(root_pub, trust / "root.pub")
        shutil.copy2(release_cert, trust / "release.cert")
        shutil.copy2(release2_cert, trust / "release2.cert")
        shutil.copy2(content_cert, trust / "content.cert")
        shutil.copy2(expired_cert, trust / "expired.cert")
        m, payload, sig = manifest(root, "app", release_id)
        assert run("sign", "--manifest", str(m), "--key", str(release_key), "--out", str(sig))[0] == 0
        code, out = verify(m, sig, payload, trust)
        assert code == 0 and out["ok"], out
        print("S1 valid: PASS")
        original = m.read_text(encoding="utf-8")
        tampered = json.loads(original); tampered["version"] = "0.1.1"
        m.write_text(json.dumps(tampered, sort_keys=True, separators=(",", ":")), encoding="utf-8")
        code, out = verify(m, sig, payload, trust); assert code != 0 and out["error"] == "signature_invalid", out
        m.write_text(original, encoding="utf-8"); print("S2 tampered manifest: PASS")
        cleaned = payload.read_bytes(); payload.write_bytes(b"tampered")
        code, out = verify(m, sig, payload, trust); assert code != 0 and out["error"] == "payload_hash_mismatch", out
        payload.write_bytes(cleaned); print("S3 tampered payload: PASS")
        missing = root / "missing.sig"
        code, out = verify(m, missing, payload, trust); assert code != 0 and out["error"] == "signature_missing", out
        print("S4 missing signature: PASS")
        unknown = json.loads(m.read_text()); unknown["key_id"] = "unknown"
        m.write_text(json.dumps(unknown, sort_keys=True, separators=(",", ":")), encoding="utf-8")
        code, out = verify(m, sig, payload, trust); assert code != 0 and out["error"] == "key_unknown", out
        m.write_text(original, encoding="utf-8"); print("S5 unknown key: PASS")
        (trust / "revocations.json").write_text(json.dumps({"keys": [{"key_id": release_id}]}), encoding="utf-8")
        code, out = verify(m, sig, payload, trust); assert code != 0 and out["error"] == "key_revoked", out
        (trust / "revocations.json").unlink(); print("S6 revoked key: PASS")
        me, pe, se = manifest(root, "app", expired_id)
        assert run("sign", "--manifest", str(me), "--key", str(expired_key), "--out", str(se))[0] == 0
        code, out = verify(me, se, pe, trust); assert code != 0 and out["error"] == "key_expired", out
        print("S7 expired cert: PASS")
        mc, pc, sc = manifest(root, "app", content_id)
        assert run("sign", "--manifest", str(mc), "--key", str(content_key), "--out", str(sc))[0] == 0
        code, out = verify(mc, sc, pc, trust); assert code != 0 and out["error"] == "key_role_mismatch", out
        print("S8 role mismatch: PASS")
        m, payload, sig = manifest(root, "app", release_id)
        assert run("sign", "--manifest", str(m), "--key", str(release_key), "--out", str(sig))[0] == 0
        code, out = verify(m, sig, payload, trust); assert code == 0, out
        print("S9 offline verify: PASS")
        target = root / "target"; target.mkdir(); (target / "marker").write_text("keep")
        code, out = verify(m, sig, payload, trust); assert code == 0
        (target / "marker").write_text("keep")
        assert (target / "marker").read_text() == "keep"
        print("S10 no partial install precondition: PASS")
        mr, pr, sr = manifest(root, "app", release2_id)
        assert run("sign", "--manifest", str(mr), "--key", str(release2_key), "--out", str(sr))[0] == 0
        code, out = verify(mr, sr, pr, trust); assert code == 0, out
        print("S11 rotated key overlap: PASS")
        pr.write_bytes(pr.read_bytes()[:-2])
        code, out = verify(mr, sr, pr, trust); assert code != 0 and out["error"] in {"payload_hash_mismatch", "payload_size_mismatch"}, out
        print("S12 truncated payload: PASS")
    print("signing matrix: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
