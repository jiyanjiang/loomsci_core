"""Deterministic research workspaces; no LLM calls."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import gate

CODE_RE = re.compile(r"^r-[0-9a-f]{12}$")
VERSION_RE = re.compile(r"^v[1-9][0-9]*$")


class ResearchError(RuntimeError):
    pass


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalize_prompt(prompt: str) -> str:
    text = re.sub(r"\s+", " ", str(prompt or "").strip())
    if not text:
        raise ResearchError("prompt required")
    return text


def prompt_code(prompt: str) -> str:
    return "r-" + hashlib.sha256(normalize_prompt(prompt).encode()).hexdigest()[:12]


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _read_json(path: Path, fallback: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return fallback


def _read_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    items = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                items.append(json.loads(line))
            except ValueError:
                pass
    return items


def _append_jsonl(path: Path, item: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(item, ensure_ascii=False) + "\n")


def _workspace_root(root: Path, code: str) -> Path:
    return root / "workspaces" / code


def _resolve(root: Path, ref: str) -> tuple[Path, dict, str, str]:
    raw = str(ref or "").strip()
    code = raw
    version = None
    if "@" in raw:
        code, version = raw.split("@", 1)
    elif "/" in raw:
        code, version = raw.split("/", 1)
    if not CODE_RE.match(code):
        raise ResearchError(f"invalid research ref: {ref}")
    base = _workspace_root(root, code)
    if not base.is_dir():
        raise ResearchError(f"workspace not found: {code}")
    versions = sorted(
        [p.name for p in base.iterdir() if p.is_dir() and VERSION_RE.match(p.name)],
        key=lambda value: int(value[1:]),
    )
    if not versions:
        raise ResearchError(f"workspace has no versions: {code}")
    version = version or versions[-1]
    if not VERSION_RE.match(version) or version not in versions:
        raise ResearchError(f"version not found: {version}")
    path = base / version
    return path, _read_json(path / "meta.json", {}), code, version


def new(prompt: str, *, root: Path, title: str = "") -> dict:
    text = normalize_prompt(prompt)
    code = prompt_code(text)
    base = _workspace_root(root, code)
    base.mkdir(parents=True, exist_ok=True)
    versions = sorted(
        [p.name for p in base.iterdir() if p.is_dir() and VERSION_RE.match(p.name)],
        key=lambda value: int(value[1:]),
    )
    version = "v" + str(len(versions) + 1)
    path = base / version
    path.mkdir(parents=True, exist_ok=False)
    meta = {
        "code": code,
        "version": version,
        "prompt": text,
        "title": title or text[:80],
        "created_at": now(),
    }
    _write_json(path / "meta.json", meta)
    (path / "OUTLINE.md").write_text(
        f"# 大纲 · {meta['title']}\n\n## 目标 / 读者\n- 目标：\n- 读者：\n\n## 结论主张\n- \n\n## 章节与资料点\n1. \n",
        encoding="utf-8",
    )
    (path / "DRAFT.md").write_text(f"# 稿 · {meta['title']}\n\n（正文）\n", encoding="utf-8")
    (path / "FACTS.md").write_text(f"# 事实库 · {meta['title']}\n\n", encoding="utf-8")
    (path / "sources.jsonl").touch()
    (path / "facts.jsonl").touch()
    return {"code": code, "version": version, "title": meta["title"], "path": str(path)}


def list_workspaces(root: Path) -> list[dict]:
    items = []
    base = root / "workspaces"
    if not base.is_dir():
        return items
    for code_dir in sorted(base.iterdir()):
        if not code_dir.is_dir() or not CODE_RE.match(code_dir.name):
            continue
        versions = sorted(
            [p.name for p in code_dir.iterdir() if p.is_dir() and VERSION_RE.match(p.name)],
            key=lambda value: int(value[1:]),
        )
        for version in versions:
            path = code_dir / version
            meta = _read_json(path / "meta.json", {})
            items.append({
                "code": code_dir.name,
                "version": version,
                "title": meta.get("title") or code_dir.name,
                "sources": len(_read_jsonl(path / "sources.jsonl")),
                "facts": len(_read_jsonl(path / "facts.jsonl")),
                "checked": (path / "check.json").is_file(),
            })
    return items


def describe(root: Path, ref: str) -> dict:
    path, meta, code, version = _resolve(root, ref)
    return {
        "code": code,
        "version": version,
        "title": meta.get("title"),
        "prompt": meta.get("prompt"),
        "sources": _read_jsonl(path / "sources.jsonl"),
        "facts": _read_jsonl(path / "facts.jsonl"),
        "draft": (path / "DRAFT.md").read_text(encoding="utf-8") if (path / "DRAFT.md").is_file() else "",
        "outline": (path / "OUTLINE.md").read_text(encoding="utf-8") if (path / "OUTLINE.md").is_file() else "",
        "check": _read_json(path / "check.json", None),
    }


def add_source(root: Path, ref: str, *, url: str, title: str = "", text: str = "", grade: str | None = None) -> dict:
    path, _meta, _code, _version = _resolve(root, ref)
    url = str(url or "").strip()
    if not url:
        raise ResearchError("url required")
    sources = _read_jsonl(path / "sources.jsonl")
    for item in sources:
        if item.get("url") == url:
            return item
    source = {
        "id": f"S{len(sources) + 1}",
        "url": url,
        "title": str(title or url)[:200],
        "text": str(text or "")[:4000],
        "grade": grade or gate.grade_for(url),
        "created_at": now(),
    }
    _append_jsonl(path / "sources.jsonl", source)
    return source


def add_fact(root: Path, ref: str, *, claim: str, url: str, quote: str = "") -> dict:
    path, meta, _code, _version = _resolve(root, ref)
    claim = str(claim or "").strip()
    url = str(url or "").strip()
    if not claim:
        raise ResearchError("claim required")
    sources = _read_jsonl(path / "sources.jsonl")
    source = next((item for item in sources if item.get("url") == url), None)
    if source is None:
        raise ResearchError("fact url must exist in sources")
    facts = _read_jsonl(path / "facts.jsonl")
    fact = {
        "id": f"F{len(facts) + 1:03d}",
        "claim": claim[:500],
        "url": url,
        "quote": str(quote or "")[:2000],
        "grade": source.get("grade", "weak"),
        "created_at": now(),
    }
    _append_jsonl(path / "facts.jsonl", fact)
    lines = [f"# 事实库 · {meta.get('title', '')}", ""]
    for item in facts + [fact]:
        lines.extend([
            f"## {item['id']}",
            f"- claim：{item['claim']}",
            f"- URL：{item['url']}",
            f"- 来源分级：{item['grade']}",
            f"- 原文摘录：{item['quote']}",
            f"- 用于：",
            "",
        ])
    (path / "FACTS.md").write_text("\n".join(lines), encoding="utf-8")
    return fact


def check(root: Path, ref: str) -> dict:
    path, meta, _code, _version = _resolve(root, ref)
    draft = (path / "DRAFT.md").read_text(encoding="utf-8") if (path / "DRAFT.md").is_file() else ""
    sources = _read_jsonl(path / "sources.jsonl")
    result = gate.evaluate(draft, sources, query_terms=str(meta.get("prompt") or "").split())
    _write_json(path / "check.json", {"checked_at": now(), **result})
    return result


def write_draft(root: Path, ref: str, text: str) -> dict:
    path, _meta, _code, _version = _resolve(root, ref)
    if not str(text or "").strip():
        raise ResearchError("draft required")
    (path / "DRAFT.md").write_text(str(text), encoding="utf-8")
    return {"ok": True, "path": str(path / "DRAFT.md")}
