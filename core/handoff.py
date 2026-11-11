"""Structured handoff posts for cross-IDE work."""

from __future__ import annotations

import json
from typing import Any

from core import storage
from core.local_auth import normalize_agent


def _list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    if isinstance(value, (list, tuple)):
        return [str(part).strip() for part in value if str(part).strip()]
    return [str(value).strip()]


def normalize(payload: dict[str, Any]) -> dict[str, Any]:
    task_id = str(payload.get("task_id") or "").strip()
    to = normalize_agent(payload.get("to"))
    evidence = payload.get("evidence")
    if not task_id:
        raise ValueError("task_id required")
    if not to:
        raise ValueError("valid to handle required")
    if not evidence:
        raise ValueError("evidence required")
    return {
        "task_id": task_id,
        "to": to,
        "completed": _list(payload.get("completed")),
        "remaining": _list(payload.get("remaining")),
        "next": _list(payload.get("next")),
        "risks": _list(payload.get("risks")),
        "evidence": evidence,
    }


def render(data: dict[str, Any]) -> str:
    lines = [
        f"# Handoff · {data['task_id']} → {data['to']}",
        "",
    ]
    for title, key in (
        ("Completed", "completed"),
        ("Remaining", "remaining"),
        ("Next", "next"),
        ("Risks", "risks"),
    ):
        lines.append(f"## {title}")
        values = data.get(key) or []
        if values:
            lines.extend(f"- {item}" for item in values)
        else:
            lines.append("- (none)")
        lines.append("")
    lines.append("## Evidence")
    evidence = data["evidence"]
    if isinstance(evidence, (dict, list)):
        lines.append("```json")
        lines.append(json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True))
        lines.append("```")
    else:
        lines.append(str(evidence))
    return "\n".join(lines).rstrip() + "\n"


def create(conn, *, author: str, payload: dict[str, Any]) -> dict[str, Any]:
    data = normalize(payload)
    task = storage.get_task(conn, data["task_id"])
    if task is None:
        raise storage.NotFound("task not found")
    return storage.create_post(
        conn,
        author=author,
        kind="handoff",
        body=render(data),
        thread_id=f"task:{data['task_id']}",
        meta={"handoff": data, "to": data["to"]},
    )
