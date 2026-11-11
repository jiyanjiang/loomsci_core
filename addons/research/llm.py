"""Optional DeepSeek adapter for research v0.2.

Key resolution order: environment, LOOMSCI_HOME config.yaml, legacy TAA local
config.toml. Keys never leave this process and are never logged.
"""

from __future__ import annotations

import json
import os
import tomllib
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

try:
    import yaml
except Exception:  # pragma: no cover - yaml is a Core dependency
    yaml = None

from . import gate

SEARCH_URL = os.environ.get("DEEPSEEK_SEARCH_URL", "https://api.deepseek.com/v1/tools/search")
CHAT_URL = os.environ.get("DEEPSEEK_CHAT_URL", "https://api.deepseek.com/chat/completions")
MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")

SOURCE_SYSTEM = (
    "你是严谨的调研助手。你只能依据下方【检索来源】回答，不得凭记忆补事实。\n"
    "规则：\n"
    "1) 每个事实性结论后必须标来源编号，如 [S1]；一个结论至少一个来源。\n"
    "2) 至少引用两个独立域名；优先官方/一手/学术来源。\n"
    "3) 来源之间冲突要并列写冲突，不要擅自选一个。\n"
    "4) 来源不足、无法核验或只有弱二手来源时，明确写「来源不足，未核验」。\n"
    "5) 严格区分事实与判断；判断标明「判断」。\n"
    "6) 不要编造 URL、标题、数字或引文。\n"
)


class LlmError(RuntimeError):
    pass


def deepseek_key(home: Path | None = None) -> str:
    for name in ("DEEPSEEK_API_KEY", "DS_KEY"):
        value = os.environ.get(name)
        if value:
            return value.strip()
    base = home or Path(os.environ.get("LOOMSCI_HOME", str(Path.home() / ".loomsci")))
    config = base / "config.yaml"
    if yaml and config.is_file():
        try:
            data = yaml.safe_load(config.read_text(encoding="utf-8")) or {}
            llm = data.get("llm") or {}
            providers = llm.get("providers") or {}
            deepseek = providers.get("deepseek") or {}
            value = deepseek.get("api_key") or llm.get("deepseek_api_key")
            if value:
                return str(value).strip()
        except Exception:
            pass
    legacy = Path.home() / ".taa" / "config.toml"
    if legacy.is_file():
        try:
            data = tomllib.loads(legacy.read_text(encoding="utf-8"))
            value = (data.get("llm") or {}).get("deepseek_api_key")
            if value:
                return str(value).strip()
        except Exception:
            pass
    return ""


def _post(url: str, key: str, payload: dict[str, Any], timeout: int = 60) -> dict:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=body, method="POST")
    request.add_header("Content-Type", "application/json")
    request.add_header("Authorization", f"Bearer {key}")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:300]
        raise LlmError(f"DeepSeek HTTP {exc.code}: {detail}") from None
    except (OSError, ValueError) as exc:
        raise LlmError(f"DeepSeek request failed: {type(exc).__name__}") from None


def search(query: str, key: str, *, limit: int = 8) -> list[dict]:
    if not key:
        raise LlmError("DeepSeek key missing")
    data = _post(SEARCH_URL, key, {
        "query": str(query or "").strip()[:128],
        "count": max(1, min(20, int(limit))),
        "need_content": True,
    }, timeout=60)
    sources = []
    for item in data.get("results") or []:
        url = str(item.get("url") or "").strip().split("#")[0]
        title = str(item.get("title") or "").strip()
        if not url or not title:
            continue
        grade = gate.grade_for(url)
        try:
            authority = int(item.get("authority") or 0)
        except (TypeError, ValueError):
            authority = 0
        if grade == "weak" and authority >= 4:
            grade = "secondary"
        text = str(item.get("content") or item.get("summary") or item.get("snippet") or "").strip()
        sources.append({
            "url": url,
            "title": title[:200],
            "text": text[:4000],
            "grade": grade,
        })
    return sources[:limit]


def answer(prompt: str, sources: list[dict], key: str, *, model: str = MODEL) -> str:
    if not key:
        raise LlmError("DeepSeek key missing")
    lines = ["【检索来源】"]
    if not sources:
        lines.append("无（未检索到可用来源）")
    for source in sources[:8]:
        lines.append(
            f"[{source.get('id') or '?'}] {source.get('title') or ''}\n"
            f"URL: {source.get('url') or ''}\n"
            f"分级: {source.get('grade') or 'unknown'}\n"
            f"摘录: {str(source.get('text') or '')[:900]}"
        )
    messages = [
        {"role": "system", "content": SOURCE_SYSTEM + "\n" + "\n\n".join(lines)},
        {"role": "user", "content": prompt},
    ]
    data = _post(CHAT_URL, key, {
        "model": model,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 4000,
    }, timeout=180)
    try:
        return str(data["choices"][0]["message"]["content"])
    except (KeyError, IndexError, TypeError):
        raise LlmError("DeepSeek returned no answer") from None
