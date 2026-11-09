"""Profile selection for loomsci_core.

`core` is the single-machine personal profile. `team` is the legacy full
capability profile. Packs can be enabled explicitly without changing profile.
"""

from __future__ import annotations

import os
from typing import Mapping

DEFAULT_PROFILE = "core"

PROFILES: dict[str, frozenset[str]] = {
    "core": frozenset({"core"}),
    "team": frozenset(
        {"core", "collab", "social", "research", "media", "sync", "dist", "lan"}
    ),
}


def resolve_profile(
    override: str | None = None,
    env: Mapping[str, str] | None = None,
) -> str:
    values = os.environ if env is None else env
    raw = str(
        override
        or values.get("LOOMSCI_PROFILE")
        or values.get("TAA_PROFILE")
        or DEFAULT_PROFILE
    ).strip().lower()
    if raw not in PROFILES:
        allowed = ", ".join(sorted(PROFILES))
        raise ValueError(f"unknown profile {raw!r}; expected one of: {allowed}")
    return raw
