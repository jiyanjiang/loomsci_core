"""Single registry for Core routes, jobs, navigation, and optional packs.

A disabled pack must not expose routes, start jobs, or appear in navigation.
The same registry is intended to be used by the HTTP app, the CLI, and the
background-job starter.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable, Mapping

from core.profile import PROFILES, resolve_profile


@dataclass(frozen=True)
class PackSpec:
    name: str
    description: str
    routes: tuple[str, ...] = ()
    jobs: tuple[str, ...] = ()
    nav: tuple[str, ...] = ()


@dataclass(frozen=True)
class GateResult:
    allowed: bool
    reason: str
    pack: str | None = None


CORE = PackSpec(
    name="core",
    description="single-machine personal workspace",
    routes=(
        "/",
        "/app",
        "/app/chats",
        "/app/tasks",
        "/app/memory",
        "/app/settings",
        "/app/diag",
        "/app/upload",
        "/static/*",
        "/thumb",
        "/avatar/*",
        "/favicon.ico",
        "/v1/health",
        "/v1/version",
        "/v1/meta/features",
        "/v1/whoami",
        "/v1/echo",
        "/v1/agents*",
        "/v1/presence*",
        "/v1/posts*",
        "/v1/tasks*",
        "/v1/handoff*",
        "/v1/inbox*",
        "/v1/read*",
        "/v1/search*",
        "/v1/memory*",
        "/v1/alice*",
        "/v1/export*",
        "/v1/import*",
        "/v1/events*",
    ),
    jobs=(),
    nav=("home", "chats", "tasks", "memory", "settings", "diagnostics"),
)

PACKS: dict[str, PackSpec] = {
    "collab": PackSpec(
        name="collab",
        description="multi-agent rooms, roles, share links, E2EE",
        routes=(
            "/v1/rooms*",
            "/v1/ui/join",
            "/app/share*",
            "/app/chats/group",
            "/app/group*",
        ),
        jobs=("group_command", "group_ingress"),
        nav=("rooms", "share"),
    ),
    "social": PackSpec(
        name="social",
        description="public feed, moments, friend visibility",
        routes=("/app/feed*", "/app/moments*", "/v1/moments*", "/v1/feed*"),
        jobs=("feed_poll",),
        nav=("feed", "moments"),
    ),
    "research": PackSpec(
        name="research",
        description="research jobs, monograph, LoomDoc pipeline",
        routes=("/v1/research*", "/app/monograph*", "/app/tools/loomdoc"),
        jobs=("research_worker",),
        nav=("research", "monograph"),
    ),
    "media": PackSpec(
        name="media",
        description="image generation, video, browse/screenshot",
        routes=("/v1/media*", "/app/fetch-image", "/v1/video*"),
        jobs=("media_worker",),
        nav=("media",),
    ),
    "sync": PackSpec(
        name="sync",
        description="center hub, peer sync, federation, discovery, tunnel",
        routes=(
            "/v1/peer*",
            "/v1/federation*",
            "/v1/center-hub*",
            "/v1/node*",
            "/v1/hub*",
            "/app/api/peer*",
            "/app/peer*",
            "/app/api/sync-now",
        ),
        jobs=("center_hub", "peer_sync", "peer_pull", "discovery"),
        nav=("sync",),
    ),
    "dist": PackSpec(
        name="dist",
        description="APK/IPA distribution",
        routes=("/v1/apps*", "/v1/dist*"),
        jobs=(),
        nav=("dist",),
    ),
    "lan": PackSpec(
        name="lan",
        description="LAN binding, pairing, multi-user access",
        routes=("/v1/lan*", "/v1/pair*"),
        jobs=("lan_listener",),
        nav=("lan",),
    ),
}


def _split_enabled(value: Iterable[str] | str | None) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, str):
        return {part.strip().lower() for part in value.split(",") if part.strip()}
    return {str(part).strip().lower() for part in value if str(part).strip()}


def _matches(pattern: str, path: str) -> bool:
    if pattern.endswith("*"):
        return path.startswith(pattern[:-1])
    return path == pattern


class Registry:
    """Resolve the active profile and gate routes/jobs/navigation."""

    def __init__(
        self,
        profile: str | None = None,
        enabled: Iterable[str] | str | None = None,
        env: Mapping[str, str] | None = None,
    ) -> None:
        self.profile = resolve_profile(profile, env)
        base = set(PROFILES[self.profile])
        extra = _split_enabled(enabled)
        values = os.environ if env is None else env
        extra |= _split_enabled(values.get("LOOMSCI_PACKS"))
        unknown = (base | extra) - set(PACKS) - {"core"}
        if unknown:
            raise ValueError(f"unknown pack(s): {', '.join(sorted(unknown))}")
        self.enabled = frozenset(base | extra | {"core"})

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "Registry":
        return cls(env=env)

    def is_enabled(self, pack: str) -> bool:
        return pack in self.enabled

    def _owner(self, path: str) -> tuple[str, str] | None:
        matches: list[tuple[int, str, str]] = []
        for spec in (CORE, *PACKS.values()):
            for pattern in spec.routes:
                if _matches(pattern, path):
                    # Longest pattern wins; Core wins ties.
                    matches.append((len(pattern), spec.name, pattern))
        if not matches:
            return None
        matches.sort(key=lambda item: (item[0], item[1] == "core"))
        _, pack, pattern = matches[-1]
        return pack, pattern

    def check_route(self, path: str) -> GateResult:
        path = str(path or "")
        if not path.startswith("/"):
            return GateResult(False, "invalid_path")
        owner = self._owner(path)
        if owner is None:
            return GateResult(False, "not_found")
        pack, _ = owner
        if pack in self.enabled:
            return GateResult(True, "ok", pack)
        return GateResult(False, "pack_disabled", pack)

    def pack_disabled_payload(self, pack: str) -> dict:
        return {"ok": False, "error": "pack_disabled", "pack": pack}

    def routes(self) -> tuple[str, ...]:
        return tuple(
            pattern
            for spec in (CORE, *PACKS.values())
            if spec.name in self.enabled
            for pattern in spec.routes
        )

    def jobs(self) -> tuple[str, ...]:
        return tuple(
            job
            for spec in (CORE, *PACKS.values())
            if spec.name in self.enabled
            for job in spec.jobs
        )

    def nav(self) -> tuple[str, ...]:
        return tuple(
            item
            for spec in (CORE, *PACKS.values())
            if spec.name in self.enabled
            for item in spec.nav
        )

    def features(self) -> dict:
        routes = sorted(self.routes())
        return {
            "profile": self.profile,
            "packs": sorted(self.enabled),
            "routes": routes,
            "route_count": len(routes),
            "jobs": sorted(self.jobs()),
            "nav": list(self.nav()),
        }
