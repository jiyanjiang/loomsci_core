#!/usr/bin/env python3
"""Apply a loomsci_core package to an installed home, with rollback.

Only the code directory is swapped. `data/`, `agents/`, `packs/`, `logs/`,
`runtime/`, and `config.yaml` are never touched.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PRODUCT = "loomsci_core"
MAX_BYTES = 200 * 1024 * 1024
MAX_MEMBERS = 10_000
PRESERVE = ("data", "agents", "packs", "logs", "runtime", "config.yaml")


class UpgradeError(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _safe(name: str) -> bool:
    if not name or name.startswith("/") or "\\" in name:
        return False
    path = PurePosixPath(name)
    return not path.is_absolute() and ".." not in path.parts and ":" not in path.parts[0]


def _extract(package: Path, destination: Path) -> Path:
    with zipfile.ZipFile(package) as zf:
        infos = zf.infolist()
        if len(infos) > MAX_MEMBERS:
            raise UpgradeError("too many members")
        if sum(info.file_size for info in infos) > MAX_BYTES:
            raise UpgradeError("package too large")
        for info in infos:
            if not _safe(info.filename):
                raise UpgradeError(f"unsafe member: {info.filename}")
            mode = (info.external_attr >> 16) & 0o170000
            if mode == 0o120000:
                raise UpgradeError(f"symlink not allowed: {info.filename}")
        zf.extractall(destination)
    candidates = list(destination.glob("*/pyproject.toml")) + list(
        destination.glob("pyproject.toml")
    )
    if not candidates:
        raise UpgradeError("package root not found")
    return candidates[0].parent


def _manifest(package: Path) -> dict:
    with zipfile.ZipFile(package) as zf:
        names = zf.namelist()
        target = next(
            (name for name in names if name.endswith("/upgrade-manifest.json")),
            None,
        )
        if target is None:
            raise UpgradeError("upgrade-manifest.json missing")
        data = json.loads(zf.read(target).decode("utf-8"))
    if data.get("product") != PRODUCT:
        raise UpgradeError("wrong product in manifest")
    return data


def _verify_signature(package: Path, signature: Path, public_key: Path) -> None:
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    except ImportError as exc:
        raise UpgradeError("cryptography is required for signature verification") from exc
    key_bytes = public_key.expanduser().read_bytes()
    sig_bytes = signature.expanduser().read_bytes()
    if len(key_bytes) != 32:
        raise UpgradeError("public key must be 32 raw bytes")
    try:
        Ed25519PublicKey.from_public_bytes(key_bytes).verify(
            sig_bytes, package.read_bytes()
        )
    except Exception as exc:  # noqa: BLE001 - normalize crypto errors
        raise UpgradeError("signature verification failed") from exc


def _refresh_launcher(home: Path) -> None:
    """Keep the installed launcher in sync with the safe-path fix."""
    bin_dir = home / "bin"
    launcher = bin_dir / "loomsci"
    if launcher.is_file():
        launcher.write_text(
            "#!/usr/bin/env sh\n"
            f'exec env PYTHONPATH="{home}/core" PYTHONSAFEPATH=1 '
            f'LOOMSCI_HOME="{home}" "{home}/venv/bin/python" -m cli.loomsci "$@"\n',
            encoding="utf-8",
        )
        launcher.chmod(0o755)
    cmd = bin_dir / "loomsci.cmd"
    if cmd.is_file():
        lines = [
            "@echo off",
            f'set "PYTHONPATH={home}\\core"',
            'set "PYTHONSAFEPATH=1"',
            f'set "LOOMSCI_HOME={home}"',
            f'"{home}\\venv\\Scripts\\python.exe" -m cli.loomsci %*',
        ]
        cmd.write_text("\r\n".join(lines) + "\r\n", encoding="ascii")


def _backup(home: Path, version: str) -> str | None:
    db = home / "data" / "data.db"
    if not db.is_file():
        return None
    from core import backup

    folder = home / "backups"
    folder.mkdir(parents=True, exist_ok=True)
    destination = folder / f"pre-upgrade-{version}.zip"
    backup.create(home, destination)
    return str(destination)


def _state(home: Path, phase: str, **extra) -> None:
    path = home / "upgrade.state.json"
    payload = {"phase": phase, "at": _now(), **extra}
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def apply(
    package: str | Path,
    home: str | Path,
    dry_run: bool = False,
    signature: str | Path | None = None,
    public_key: str | Path | None = None,
    backup: bool = True,
) -> dict:
    package = Path(package).expanduser()
    home = Path(home).expanduser()
    if not package.is_file():
        raise UpgradeError("package not found")
    if bool(signature) != bool(public_key):
        raise UpgradeError("--signature and --public-key must be used together")
    if signature and public_key:
        _verify_signature(package, Path(signature), Path(public_key))
    manifest = _manifest(package)
    if dry_run:
        return {"ok": True, "dry_run": True, "manifest": manifest}

    home.mkdir(parents=True, exist_ok=True)
    backup_path = None
    if backup:
        _state(home, "PREFLIGHT", package=str(package))
        backup_path = _backup(home, str(manifest.get("package_version") or "unknown"))
        _state(home, "BACKED_UP", package=str(package), backup=backup_path)
    _state(home, "PREFLIGHT", package=str(package))
    staging = Path(tempfile.mkdtemp(prefix="loomsci-upgrade-", dir=str(home)))
    new_core: Path | None = None
    try:
        new_core = _extract(package, staging)
        _state(home, "STAGED", package=str(package))
        core = home / "core"
        previous = home / "core.prev"
        if core.exists():
            shutil.rmtree(previous, ignore_errors=True)
            core.rename(previous)
        shutil.move(str(new_core), str(core))
        _refresh_launcher(home)
        _state(home, "SWAPPED", package=str(package))
        _state(home, "COMMITTED", package=str(package))
        return {"ok": True, "home": str(home), "manifest": manifest, "backup": backup_path}
    except Exception as exc:
        core = home / "core"
        previous = home / "core.prev"
        if previous.exists() and not core.exists():
            shutil.move(str(previous), str(core))
        _state(home, "ROLLED_BACK", error=str(exc)[:300])
        raise
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def rollback(home: str | Path) -> dict:
    home = Path(home).expanduser()
    core = home / "core"
    previous = home / "core.prev"
    if not previous.exists():
        raise UpgradeError("no previous core to restore")
    if core.exists():
        shutil.rmtree(core)
    shutil.move(str(previous), str(core))
    _state(home, "ROLLED_BACK", reason="manual")
    return {"ok": True, "home": str(home)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="upgrade")
    parser.add_argument("--package")
    parser.add_argument("--home", default=str(Path.home() / ".loomsci"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--rollback", action="store_true")
    parser.add_argument("--signature")
    parser.add_argument("--public-key")
    parser.add_argument("--no-backup", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.rollback:
            result = rollback(args.home)
        else:
            if not args.package:
                parser.error("--package is required unless --rollback is used")
            result = apply(
                args.package,
                args.home,
                dry_run=args.dry_run,
                signature=args.signature,
                public_key=args.public_key,
                backup=not args.no_backup,
            )
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
