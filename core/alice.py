"""Default agent baseline, rename history, and persona snapshots."""

from __future__ import annotations

import json
import os
import re
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from core import storage

ROOT = Path(__file__).resolve().parent.parent
BASELINE = ROOT / "presets" / "agents" / "alice"
SHORT_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,31}$")
OWNER_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,31}$")


class AliceError(RuntimeError):
    pass


def _chmod(path: Path, mode: int = 0o600) -> None:
    try:
        os.chmod(path, mode)
    except OSError:
        pass


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _validate_short(short: str) -> str:
    value = str(short or "").strip().lower()
    if not SHORT_RE.fullmatch(value):
        raise AliceError("agent short name must be lowercase letters/digits/hyphen")
    return value


def _validate_owner(owner: str) -> str:
    value = str(owner or "").strip().lower()
    if not OWNER_RE.fullmatch(value):
        raise AliceError("owner must be lowercase letters/digits/hyphen (no dots)")
    return value


def agent_dir(home: str | Path, short: str = "alice") -> Path:
    return Path(home).expanduser() / "agents" / _validate_short(short)


def baseline_persona() -> dict[str, Any]:
    path = BASELINE / "persona.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise AliceError("baseline persona must be a mapping")
    return data


def _render(
    text: str, *, handle: str, owner: str, short: str, cli: str
) -> str:
    return (
        text.replace("{{HANDLE}}", handle)
        .replace("{{OWNER}}", owner)
        .replace("{{SHORT}}", short)
        .replace("{{CLI}}", cli)
    )


def read_agent(home: str | Path, short: str = "alice") -> dict[str, Any] | None:
    path = agent_dir(home, short) / "agent.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def ensure(
    home: str | Path,
    owner: str,
    short: str = "alice",
    role: str = "personal_assistant",
    default_tool: str | None = None,
) -> dict[str, Any]:
    """Create an agent from the baseline; idempotent."""

    owner = _validate_owner(owner)
    short = _validate_short(short)
    handle = f"{short}.{owner}"
    target = agent_dir(home, short)
    existing = read_agent(home, short)
    if existing:
        return existing
    if not BASELINE.is_dir():
        raise AliceError(f"baseline missing: {BASELINE}")

    for name in ("skills", "experience", "versions", "inbox"):
        (target / name).mkdir(parents=True, exist_ok=True)
    _chmod(target, 0o700)

    persona = yaml.safe_load((BASELINE / "persona.yaml").read_text(encoding="utf-8"))
    if isinstance(persona, dict):
        identity = persona.setdefault("identity", {})
        identity["name"] = short[:1].upper() + short[1:]
        identity["short"] = short
        identity["role"] = role
        (target / "persona.yaml").write_text(
            yaml.safe_dump(persona, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        _chmod(target / "persona.yaml")
    else:
        shutil.copy2(BASELINE / "persona.yaml", target / "persona.yaml")
    cli = str(Path(home).expanduser() / "bin" / "loomsci")
    instructions = (BASELINE / "instructions.md").read_text(encoding="utf-8")
    instructions = _render(
        instructions, handle=handle, owner=owner, short=short, cli=cli
    )
    if role != "personal_assistant":
        instructions = instructions.replace(
            "the default personal agent", "a collaborating agent"
        )
    (target / "instructions.md").write_text(instructions, encoding="utf-8")
    _chmod(target / "instructions.md")

    adapters = BASELINE / "adapters"
    if adapters.is_dir():
        for source in adapters.glob("*.md"):
            text = source.read_text(encoding="utf-8")
            (target / "adapters").mkdir(exist_ok=True)
            (target / "adapters" / source.name).write_text(
                _render(
                    text, handle=handle, owner=owner, short=short, cli=cli
                ),
                encoding="utf-8",
            )
            _chmod(target / "adapters" / source.name)

    record = {
        "handle": handle,
        "short": short,
        "owner": owner,
        "role": role,
        "created_at": _now(),
        "default_tool": default_tool,
    }
    (target / "agent.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    _chmod(target / "agent.json")
    return record


def _write_record(home: str | Path, short: str, record: dict[str, Any]) -> None:
    path = agent_dir(home, short) / "agent.json"
    path.write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    _chmod(path)


def rename(
    home: str | Path,
    conn: sqlite3.Connection,
    old_short: str,
    new_short: str,
    owner: str | None = None,
) -> dict[str, Any]:
    old_short = _validate_short(old_short)
    new_short = _validate_short(new_short)
    if old_short == new_short:
        raise AliceError("new short name must differ")
    record = read_agent(home, old_short)
    if not record:
        raise AliceError(f"agent not found: {old_short}")
    owner = _validate_owner(owner or record.get("owner", ""))
    old_handle = str(record.get("handle") or f"{old_short}.{owner}")
    new_handle = f"{new_short}.{owner}"

    old_dir = agent_dir(home, old_short)
    new_dir = agent_dir(home, new_short)
    if new_dir.exists():
        raise AliceError(f"target agent already exists: {new_short}")

    old_dir.rename(new_dir)
    record.update({"handle": new_handle, "short": new_short, "owner": owner})
    _write_record(home, new_short, record)

    history_path = new_dir / "renames.json"
    try:
        history = json.loads(history_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        history = []
    history.append({"from": old_handle, "to": new_handle, "at": _now()})
    history_path.write_text(
        json.dumps(history, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    storage.ensure_agent(conn, new_handle)
    storage.record_alias(conn, old_handle, new_handle)
    return record


def snapshot(
    home: str | Path,
    short: str = "alice",
    reason: str = "manual",
) -> Path:
    directory = agent_dir(home, short)
    persona = directory / "persona.yaml"
    if not persona.is_file():
        raise AliceError("persona.yaml missing")
    safe_reason = re.sub(r"[^A-Za-z0-9_.-]", "_", reason)[:40] or "manual"
    target = directory / "versions" / f"{_stamp()}-{safe_reason}.yaml"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(persona, target)
    _chmod(target)
    return target


def review(home: str | Path, short: str = "alice") -> dict[str, Any]:
    directory = agent_dir(home, short)
    record = read_agent(home, short)
    versions = []
    versions_dir = directory / "versions"
    if versions_dir.is_dir():
        for path in sorted(versions_dir.glob("*.yaml")):
            versions.append({
                "name": path.name,
                "bytes": path.stat().st_size,
            })
    return {
        "agent": record,
        "persona": baseline_persona() if not (directory / "persona.yaml").is_file()
        else yaml.safe_load((directory / "persona.yaml").read_text(encoding="utf-8")),
        "versions": versions,
    }


def reset(
    home: str | Path,
    short: str = "alice",
    *,
    keep_memory: bool = True,
) -> dict[str, Any]:
    directory = agent_dir(home, short)
    if not directory.is_dir():
        raise AliceError(f"agent not found: {short}")
    snapshot(home, short, reason="before-reset")
    shutil.copy2(BASELINE / "persona.yaml", directory / "persona.yaml")
    _chmod(directory / "persona.yaml")
    record = read_agent(home, short)
    if record:
        instructions = (BASELINE / "instructions.md").read_text(encoding="utf-8")
        (directory / "instructions.md").write_text(
            _render(
                instructions,
                handle=str(record.get("handle") or f"{short}.<owner>"),
                owner=str(record.get("owner") or "<owner>"),
                short=short,
                cli=str(directory.parent.parent / "bin" / "loomsci"),
            ),
            encoding="utf-8",
        )
    if not keep_memory:
        memory = directory / "memory.db"
        if memory.exists():
            archived = directory / "versions" / f"{_stamp()}-memory.db"
            archived.parent.mkdir(parents=True, exist_ok=True)
            memory.rename(archived)
    return {"ok": True, "agent": record, "keep_memory": keep_memory}
