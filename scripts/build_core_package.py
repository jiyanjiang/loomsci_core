#!/usr/bin/env python3
"""Build a signed Core package directory for the C1 layout.

Not a release tool. Produces:
  <out>/manifest.json
  <out>/manifest.sig
  <out>/payload.tar.gz
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import tarfile
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parent.parent


def canonical(data: dict) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--private-key", required=True)
    parser.add_argument("--version", default="0.1.0")
    args = parser.parse_args()
    out = Path(args.out).expanduser()
    if out.exists():
        raise SystemExit(f"output exists: {out}")
    out.mkdir(parents=True)
    payload = out / "payload.tar.gz"
    with tarfile.open(payload, "w:gz") as archive:
        for name in ("loomsci_core", "requirements-core.txt", "examples/hello-app", "docs/en/core-v0", "docs/zh-CN/core-v0", "docs/openapi/core-v0.json"):
            path = ROOT / name
            if path.exists():
                archive.add(path, arcname=name)
    digest = hashlib.sha256(payload.read_bytes()).hexdigest()
    manifest = {
        "kind": "core",
        "name": "loomsci_core",
        "version": args.version,
        "platform": "any",
        "created_at": __import__("time").strftime("%Y-%m-%dT%H:%M:%SZ", __import__("time").gmtime()),
        "payload_sha256": digest,
        "payload_bytes": payload.stat().st_size,
        "key_id": None,
    }
    key = Ed25519PrivateKey.from_private_bytes(Path(args.private_key).read_bytes())
    from cryptography.hazmat.primitives import serialization
    key_id = hashlib.sha256(key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )).hexdigest()[:16]
    manifest["key_id"] = key_id
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "manifest.sig").write_text(base64.b64encode(key.sign(canonical(manifest))).decode("ascii") + "\n", encoding="ascii")
    print(json.dumps({"package": str(out), "sha256": digest, "key_id": key_id}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
