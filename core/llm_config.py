"""Provider configuration shared by Core, summaries, and add-ons."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

try:
    import yaml
except Exception:  # pragma: no cover - PyYAML is a Core dependency
    yaml = None

PROVIDERS: dict[str, dict[str, str]] = {
    "deepseek": {
        "label": "DeepSeek",
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-chat",
    },
    "aliyun": {
        "label": "Alibaba DashScope",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen-plus",
    },
    "volcengine": {
        "label": "Volcengine Ark",
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "model": "",
    },
}


def config_path(home: str | Path) -> Path:
    return Path(home).expanduser() / "config.yaml"


def _load(home: str | Path) -> dict[str, Any]:
    path = config_path(home)
    if not path.is_file() or yaml is None:
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _providers(data: dict[str, Any]) -> dict[str, Any]:
    llm = data.get("llm")
    if not isinstance(llm, dict):
        llm = {}
        data["llm"] = llm
    providers = llm.get("providers")
    if not isinstance(providers, dict):
        providers = {}
        llm["providers"] = providers
    return providers


def _provider_config(data: dict[str, Any], provider: str) -> dict[str, Any]:
    providers = _providers(data)
    current = providers.get(provider)
    if not isinstance(current, dict):
        current = {}
        providers[provider] = current
    preset = PROVIDERS.get(provider, {})
    current.setdefault("label", preset.get("label", provider))
    current.setdefault("base_url", preset.get("base_url", ""))
    current.setdefault("model", preset.get("model", ""))
    current.setdefault("api_key", "")
    return current


def _legacy_key(data: dict[str, Any], provider: str) -> str:
    if provider != "deepseek":
        return ""
    llm = data.get("llm") if isinstance(data.get("llm"), dict) else {}
    return str(llm.get("deepseek_api_key") or "").strip()


def get_key(home: str | Path | None, provider: str = "deepseek") -> str:
    for env_name in ("DEEPSEEK_API_KEY", "DS_KEY") if provider == "deepseek" else ():
        value = os.environ.get(env_name)
        if value:
            return str(value).strip()
    if home is None:
        return ""
    data = _load(home)
    current = _provider_config(data, provider)
    value = str(current.get("api_key") or "").strip()
    return value or _legacy_key(data, provider)


def public(home: str | Path, provider: str = "deepseek") -> dict[str, Any]:
    data = _load(home)
    current = _provider_config(data, provider)
    preset = PROVIDERS.get(provider, {})
    return {
        "id": provider,
        "label": str(current.get("label") or preset.get("label") or provider),
        "base_url": str(current.get("base_url") or preset.get("base_url") or ""),
        "model": str(current.get("model") or preset.get("model") or ""),
        "configured": bool(get_key(home, provider)),
    }


def _write(home: str | Path, data: dict[str, Any]) -> None:
    if yaml is None:
        raise RuntimeError("PyYAML is required for provider settings")
    path = config_path(home)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".yaml.tmp")
    tmp.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    tmp.chmod(0o600)
    os.replace(tmp, path)
    path.chmod(0o600)


def set_key(home: str | Path, provider: str, api_key: str) -> dict[str, Any]:
    data = _load(home)
    current = _provider_config(data, provider)
    key = str(api_key or "").strip()
    if key:
        current["api_key"] = key
    else:
        current.pop("api_key", None)
    if provider == "deepseek":
        llm = data.get("llm") if isinstance(data.get("llm"), dict) else {}
        llm.pop("deepseek_api_key", None)
        data["llm"] = llm
    _write(home, data)
    return public(home, provider)


def set_fields(
    home: str | Path,
    provider: str,
    *,
    base_url: str | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    data = _load(home)
    current = _provider_config(data, provider)
    if base_url is not None:
        current["base_url"] = str(base_url).strip()
    if model is not None:
        current["model"] = str(model).strip()
    _write(home, data)
    return public(home, provider)


def test_connection(home: str | Path, provider: str = "deepseek") -> dict[str, Any]:
    current = public(home, provider)
    key = get_key(home, provider)
    if not key:
        return {"ok": False, "error": "api_key_missing"}
    base = current["base_url"].rstrip("/")
    model = current["model"]
    if not base or not model:
        return {"ok": False, "error": "provider_incomplete"}
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 1,
    }).encode("utf-8")
    request = urllib.request.Request(
        base + "/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    started = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            response.read()
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            return {"ok": False, "error": "authentication_failed"}
        return {"ok": False, "error": f"http_{exc.code}"}
    except (OSError, ValueError):
        return {"ok": False, "error": "connection_failed"}
    return {
        "ok": True,
        "latency_ms": int((time.monotonic() - started) * 1000),
        "model": model,
    }
