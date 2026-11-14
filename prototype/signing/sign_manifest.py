#!/usr/bin/env python3
"""Minimal Ed25519 manifest signing prototype for the M0 contract.

Not product code. It validates canonical manifest signing, payload binding,
and failure modes on macOS and Windows.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.exceptions import InvalidSignature


def canonical(data: dict) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def key_id(public: Ed25519PublicKey) -> str:
    return hashlib.sha256(public.public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )).hexdigest()[:16]


def cmd_keygen(args: argparse.Namespace) -> int:
    private = Ed25519PrivateKey.generate()
    public = private.public_key()
    Path(args.private).write_bytes(private.private_bytes(
        serialization.Encoding.Raw,
        serialization.PrivateFormat.Raw,
        serialization.NoEncryption(),
    ))
    Path(args.public).write_bytes(public.public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    ))
    print(json.dumps({"key_id": key_id(public)}))
    return 0


def _load_public(path: str) -> Ed25519PublicKey:
    return Ed25519PublicKey.from_public_bytes(Path(path).read_bytes())


def cmd_sign(args: argparse.Namespace) -> int:
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    private = Ed25519PrivateKey.from_private_bytes(Path(args.key).read_bytes())
    signature = private.sign(canonical(manifest))
    Path(args.out).write_text(base64.b64encode(signature).decode("ascii") + "\n", encoding="utf-8")
    print(json.dumps({"signed": True, "key_id": key_id(private.public_key())}))
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    try:
        manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
        public = _load_public(args.public)
        signature = base64.b64decode(Path(args.sig).read_text(encoding="ascii").strip())
        public.verify(signature, canonical(manifest))
        payload = Path(args.payload).read_bytes()
        if hashlib.sha256(payload).hexdigest() != manifest.get("payload_sha256"):
            raise ValueError("payload_hash_mismatch")
        if len(payload) != int(manifest.get("payload_bytes", -1)):
            raise ValueError("payload_size_mismatch")
        print(json.dumps({"ok": True, "key_id": key_id(public)}))
        return 0
    except InvalidSignature:
        print(json.dumps({"ok": False, "error": "signature_invalid"}))
        return 1
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 1


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    keygen = sub.add_parser("keygen")
    keygen.add_argument("--private", required=True)
    keygen.add_argument("--public", required=True)
    keygen.set_defaults(func=cmd_keygen)
    sign = sub.add_parser("sign")
    sign.add_argument("--manifest", required=True)
    sign.add_argument("--key", required=True)
    sign.add_argument("--out", required=True)
    sign.set_defaults(func=cmd_sign)
    verify = sub.add_parser("verify")
    verify.add_argument("--manifest", required=True)
    verify.add_argument("--sig", required=True)
    verify.add_argument("--public", required=True)
    verify.add_argument("--payload", required=True)
    verify.set_defaults(func=cmd_verify)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
