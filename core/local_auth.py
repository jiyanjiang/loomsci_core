"""Local request boundary for the single-machine host.

There is no user login. The boundary is: loopback host, local origin, a
declared agent handle, and JSON for writes. This module is framework-free so
the same rules can be used by the HTTP app and tests.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlsplit

from core.packs import Registry

LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}
PUBLIC_PATHS = frozenset({
    "/",
    "/app",
    "/v1/health",
    "/v1/version",
    "/v1/meta/features",
})
PUBLIC_PREFIXES = ("/static/", "/thumb", "/avatar/", "/favicon.ico")
HANDLE_RE = re.compile(
    r"^[a-z0-9][a-z0-9-]{0,31}\.[a-z0-9][a-z0-9-]{0,31}$"
)
WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


@dataclass(frozen=True)
class GateDecision:
    ok: bool
    status: int = 200
    payload: dict | None = None
    agent: str | None = None


def _host_parts(host: str) -> tuple[str, int | None]:
    raw = str(host or "").strip()
    if not raw:
        return "", None
    if raw.startswith("["):
        end = raw.find("]")
        if end == -1:
            return raw.lower(), None
        name = raw[1:end].lower()
        rest = raw[end + 1:]
        if rest.startswith(":") and rest[1:].isdigit():
            return name, int(rest[1:])
        return name, None
    if raw.count(":") == 1:
        name, maybe_port = raw.rsplit(":", 1)
        if maybe_port.isdigit():
            return name.lower(), int(maybe_port)
    return raw.lower(), None


def is_loopback_host(host: str) -> bool:
    name, _ = _host_parts(host)
    return name in LOOPBACK_HOSTS


def origin_allowed(origin: str | None, host: str) -> bool:
    if not origin:
        return True
    if origin == "null":
        return False
    try:
        parsed = urlsplit(origin)
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    hostname = (parsed.hostname or "").lower()
    if hostname not in LOOPBACK_HOSTS:
        return False
    _, request_port = _host_parts(host)
    origin_port = parsed.port or (443 if parsed.scheme == "https" else 80)
    if request_port is not None and origin_port != request_port:
        return False
    return True


def normalize_agent(value: str | None) -> str | None:
    raw = str(value or "").strip().lower()
    if not HANDLE_RE.fullmatch(raw):
        return None
    short, _, owner = raw.partition(".")
    if not short or not owner:
        return None
    return raw


def _deny(status: int, error: str, **extra) -> GateDecision:
    return GateDecision(False, status, {"ok": False, "error": error, **extra})


def check_request(
    *,
    method: str,
    path: str,
    host: str,
    registry: Registry,
    origin: str | None = None,
    content_type: str | None = None,
    agent: str | None = None,
) -> GateDecision:
    """Apply Host, Origin, pack, identity, and JSON rules in order."""

    if not is_loopback_host(host):
        return _deny(403, "bad_host")
    if not origin_allowed(origin, host):
        return _deny(403, "bad_origin")

    route = registry.check_route(path)
    if not route.allowed:
        if route.reason == "pack_disabled":
            return _deny(404, "pack_disabled", pack=route.pack)
        return _deny(404, "not_found")

    if path in PUBLIC_PATHS or path.startswith(PUBLIC_PREFIXES):
        return GateDecision(True, agent=None)

    handle = normalize_agent(agent)
    if handle is None:
        if not str(agent or "").strip():
            return _deny(401, "login_required")
        return _deny(400, "bad_agent_handle")

    if method.upper() in WRITE_METHODS:
        media_type = (content_type or "").split(";", 1)[0].strip().lower()
        if media_type != "application/json":
            return _deny(415, "json_required")

    return GateDecision(True, agent=handle)
