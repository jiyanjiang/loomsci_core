from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.packs import Registry  # noqa: E402
from core.profile import resolve_profile  # noqa: E402


class ProfileTest(unittest.TestCase):
    def test_default_is_core(self) -> None:
        self.assertEqual(resolve_profile(env={}), "core")

    def test_taa_profile_alias(self) -> None:
        self.assertEqual(resolve_profile(env={"TAA_PROFILE": "team"}), "team")

    def test_invalid_profile_fails(self) -> None:
        with self.assertRaises(ValueError):
            resolve_profile(env={"LOOMSCI_PROFILE": "other"})


class RegistryTest(unittest.TestCase):
    def test_core_route_allowed(self) -> None:
        registry = Registry(profile="core")
        self.assertTrue(registry.check_route("/v1/health").allowed)
        self.assertTrue(registry.check_route("/app/chats").allowed)

    def test_disabled_pack_route_is_blocked(self) -> None:
        registry = Registry(profile="core")
        result = registry.check_route("/v1/peer/events")
        self.assertFalse(result.allowed)
        self.assertEqual(result.reason, "pack_disabled")
        self.assertEqual(result.pack, "sync")
        self.assertEqual(
            registry.pack_disabled_payload("sync"),
            {"ok": False, "error": "pack_disabled", "pack": "sync"},
        )

    def test_disabled_pack_jobs_and_nav_absent(self) -> None:
        registry = Registry(profile="core")
        self.assertNotIn("center_hub", registry.jobs())
        self.assertNotIn("sync", registry.nav())
        self.assertNotIn("feed", registry.nav())

    def test_team_profile_enables_pack(self) -> None:
        registry = Registry(profile="team")
        self.assertTrue(registry.check_route("/v1/peer/events").allowed)
        self.assertIn("center_hub", registry.jobs())
        self.assertIn("sync", registry.nav())

    def test_explicit_pack_enable(self) -> None:
        registry = Registry(profile="core", enabled=["sync"])
        self.assertTrue(registry.check_route("/v1/peer/events").allowed)
        self.assertIn("center_hub", registry.jobs())

    def test_env_pack_enable(self) -> None:
        registry = Registry(env={"LOOMSCI_PROFILE": "core", "LOOMSCI_PACKS": "sync"})
        self.assertTrue(registry.check_route("/v1/federation/policy").allowed)

    def test_unknown_pack_fails(self) -> None:
        with self.assertRaises(ValueError):
            Registry(profile="core", enabled=["nope"])

    def test_features_budget_and_no_disabled_routes(self) -> None:
        registry = Registry(profile="core")
        features = registry.features()
        self.assertEqual(features["profile"], "core")
        self.assertLessEqual(features["route_count"], 80)
        self.assertNotIn("/v1/peer*", features["routes"])
        self.assertNotIn("/app/feed*", features["routes"])
        self.assertEqual(features["jobs"], [])

    def test_unknown_route(self) -> None:
        registry = Registry(profile="core")
        result = registry.check_route("/v1/not-a-route")
        self.assertFalse(result.allowed)
        self.assertEqual(result.reason, "not_found")
        self.assertIsNone(result.pack)


if __name__ == "__main__":
    unittest.main()
