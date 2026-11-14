"""Minimal local/remote tool catalog."""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path
from typing import Any

FORMAT = "loomsci-catalog/1"


class CatalogError(ValueError):
    pass


def load(source: str, timeout: int = 15) -> dict[str, Any]:
    source = str(source or "").strip()
    if not source:
        raise CatalogError("catalog source required")
    if source.startswith(("http://", "https://")):
        if not source.startswith("https://"):
            raise CatalogError("catalog must use HTTPS")
        try:
            with urllib.request.urlopen(source, timeout=timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001 - remote boundary
            raise CatalogError(f"catalog fetch failed: {exc}") from exc
    else:
        path = Path(source).expanduser()
        if not path.is_file():
            raise CatalogError("catalog file not found")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except ValueError as exc:
            raise CatalogError("catalog is not JSON") from exc

    if not isinstance(data, dict) or data.get("format") != FORMAT:
        raise CatalogError("unsupported catalog format")
    apps = data.get("apps")
    if not isinstance(apps, list):
        raise CatalogError("catalog apps must be a list")
    clean = []
    for app in apps:
        if not isinstance(app, dict):
            continue
        slug = str(app.get("slug") or "").strip()
        name = str(app.get("name") or "").strip()
        version = str(app.get("version") or "").strip()
        repo = str(app.get("repo") or "").strip()
        local = str(app.get("source") or "").strip()
        if not slug or not name or not version or not (repo or local):
            continue
        if repo and not repo.startswith("https://github.com/"):
            raise CatalogError(f"unsupported repo for {slug}")
        clean.append({
            "slug": slug,
            "name": name,
            "version": version,
            "description": str(app.get("description") or ""),
            "repo": repo,
            "source": local,
        })
    return {"format": FORMAT, "apps": clean}
