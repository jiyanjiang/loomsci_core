#!/usr/bin/env python3
"""Minimal trust/certificate prototype for the M0 signing contract.

Not product code. It validates root -> release/content certs, role checks,
expiry, revocation, manifest signatures, and payload binding.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


def canonical(data: dict) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def key_id(public: Ed25519PublicKey) -> str:
    return hashlib.sha256(public.public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )).hexdigest()[:16]


def _public_from_b64(value: str) -> Ed25519PublicKey:
    return Ed25519PublicKey.from_public_bytes(base64.b64decode(value))


def _public_from_file(path: Path) -> Ed25519PublicKey:
    return Ed25519PublicKey.from_public_bytes(path.read_bytes())


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


def cmd_certify(args: argparse.Namespace) -> int:
    root = Ed25519PrivateKey.from_private_bytes(Path(args.root_key).read_bytes())
    public = _public_from_file(Path(args.public))
    now = datetime.now(timezone.utc).replace(microsecond=0)
    if args.expires:
        expires = datetime.fromisoformat(args.expires.replace("Z", "+00:00"))
    else:
        expires = now + timedelta(days=365)
    cert = {
        "kind": "cert",
        "role": args.role,
        "key_id": key_id(public),
        "public_key": base64.b64encode(public.public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )).decode("ascii"),
        "issued_at": now.isoformat(),
        "expires_at": expires.isoformat(),
        "root_key_id": key_id(root.public_key()),
    }
    cert["signature"] = base64.b64encode(root.sign(canonical(cert))).decode("ascii")
    Path(args.out).write_text(json.dumps(cert, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"certified": True, "role": args.role, "key_id": cert["key_id"]}))
    return 0


def _load_certs(trust: Path) -> list[dict]:
    certs = []
    for path in sorted(trust.glob("*.cert")):
        try:
            cert = json.loads(path.read_text(encoding="utf-8"))
            cert["_path"] = str(path)
            certs.append(cert)
        except Exception:
            continue
    return certs


def _cert_ok(cert: dict, root: Ed25519PublicKey) -> bool:
    body = {key: value for key, value in cert.items() if key not in {"signature", "_path"}}
    try:
        root.verify(base64.b64decode(cert["signature"]), canonical(body))
        return True
    except Exception:
        return False


def _revoked(trust: Path, key: str) -> bool:
    path = trust / "revocations.json"
    if not path.is_file():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return any(item.get("key_id") == key for item in data.get("keys") or [])
    except Exception:
        return False


def cmd_verify(args: argparse.Namespace) -> int:
    trust = Path(args.trust)
    try:
        manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
        sig_path = Path(args.sig)
        if not sig_path.is_file():
            raise ValueError("signature_missing")
        signature = base64.b64decode(sig_path.read_text(encoding="ascii").strip())
        payload = Path(args.payload).read_bytes()
        role = "content" if manifest.get("kind") == "content" else "release"
        kind = manifest.get("kind")
        if kind == "content" and role != "content":
            raise ValueError("key_role_mismatch")
        if kind in {"core", "app"} and role != "release":
            raise ValueError("key_role_mismatch")
        root = _public_from_file(trust / "root.pub")
        certs = _load_certs(trust)
        cert = next((item for item in certs if item.get("key_id") == manifest.get("key_id")), None)
        if cert is None:
            raise ValueError("key_unknown")
        if not _cert_ok(cert, root):
            raise ValueError("cert_invalid")
        if cert.get("role") != role:
            raise ValueError("key_role_mismatch")
        expires = datetime.fromisoformat(str(cert.get("expires_at")).replace("Z", "+00:00"))
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires < datetime.now(timezone.utc):
            raise ValueError("key_expired")
        if _revoked(trust, str(cert.get("key_id"))):
            raise ValueError("key_revoked")
        public = _public_from_b64(cert["public_key"])
        public.verify(signature, canonical(manifest))
        if hashlib.sha256(payload).hexdigest() != manifest.get("payload_sha256"):
            raise ValueError("payload_hash_mismatch")
        if len(payload) != int(manifest.get("payload_bytes", -1)):
            raise ValueError("payload_size_mismatch")
        print(json.dumps({"ok": True, "role": role, "key_id": cert["key_id"]}))
        return 0
    except InvalidSignature:
        print(json.dumps({"ok": False, "error": "signature_invalid"}))
        return 1
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 1


def cmd_sign(args: argparse.Namespace) -> int:
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    private = Ed25519PrivateKey.from_private_bytes(Path(args.key).read_bytes())
    Path(args.out).write_text(
        base64.b64encode(private.sign(canonical(manifest))).decode("ascii") + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"signed": True, "key_id": key_id(private.public_key())}))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    keygen = sub.add_parser("keygen")
    keygen.add_argument("--private", required=True)
    keygen.add_argument("--public", required=True)
    keygen.set_defaults(func=cmd_keygen)
    certify = sub.add_parser("certify")
    certify.add_argument("--root-key", required=True)
    certify.add_argument("--public", required=True)
    certify.add_argument("--role", choices=("release", "content"), required=True)
    certify.add_argument("--expires")
    certify.add_argument("--out", required=True)
    certify.set_defaults(func=cmd_certify)
    sign = sub.add_parser("sign")
    sign.add_argument("--manifest", required=True)
    sign.add_argument("--key", required=True)
    sign.add_argument("--out", required=True)
    sign.set_defaults(func=cmd_sign)
    verify = sub.add_parser("verify")
    verify.add_argument("--manifest", required=True)
    verify.add_argument("--sig", required=True)
    verify.add_argument("--payload", required=True)
    verify.add_argument("--trust", required=True)
    verify.set_defaults(func=cmd_verify)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
