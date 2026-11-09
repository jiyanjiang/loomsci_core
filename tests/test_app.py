from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.app import create_app  # noqa: E402
from core.local_auth import (  # noqa: E402
    is_loopback_host,
    normalize_agent,
    origin_allowed,
)

AGENT = "alice.jiyanjiang"


class LocalAuthPureTest(unittest.TestCase):
    def test_loopback_hosts(self) -> None:
        for host in ("127.0.0.1", "localhost", "[::1]", "127.0.0.1:8787"):
            self.assertTrue(is_loopback_host(host), host)
        for host in ("0.0.0.0", "203.0.113.5", "evil.example"):
            self.assertFalse(is_loopback_host(host), host)

    def test_agent_handle(self) -> None:
        self.assertEqual(normalize_agent(AGENT), AGENT)
        self.assertIsNone(normalize_agent("alice"))
        self.assertIsNone(normalize_agent("alice.jiyanjiang.extra"))
        self.assertIsNone(normalize_agent("Alice Jiyanjiang"))

    def test_origin(self) -> None:
        self.assertTrue(origin_allowed(None, "localhost:8787"))
        self.assertTrue(origin_allowed("http://127.0.0.1:8787", "127.0.0.1:8787"))
        self.assertFalse(origin_allowed("https://evil.example", "127.0.0.1:8787"))
        self.assertFalse(origin_allowed("http://127.0.0.1:9999", "127.0.0.1:8787"))
        self.assertFalse(origin_allowed("null", "127.0.0.1:8787"))


class AppTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        home = Path(self.tmp.name) / "home"
        self.app = create_app(env={"LOOMSCI_PROFILE": "core"}, home=home)
        self.app.testing = True
        self.client = self.app.test_client()

    def test_health_public(self) -> None:
        response = self.client.get("/v1/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["service"], "loomsci_core")

    def test_status_page_public(self) -> None:
        response = self.client.get("/app")
        self.assertEqual(response.status_code, 200)
        self.assertIn("loomsci_core", response.get_data(as_text=True))
        root = self.client.get("/")
        self.assertEqual(root.status_code, 200)

    def test_features_public_and_budgeted(self) -> None:
        response = self.client.get("/v1/meta/features")
        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(response.json["route_count"], 80)
        self.assertNotIn("/v1/peer*", response.json["routes"])

    def test_anonymous_read_is_closed(self) -> None:
        response = self.client.get("/v1/whoami")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json["error"], "login_required")

    def test_identity_header_allows_read(self) -> None:
        response = self.client.get(
            "/v1/whoami", headers={"X-Loomsci-Agent": AGENT}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["agent"], AGENT)

    def test_bad_agent_handle(self) -> None:
        response = self.client.get(
            "/v1/whoami", headers={"X-Loomsci-Agent": "alice"}
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json["error"], "bad_agent_handle")

    def test_bad_host(self) -> None:
        response = self.client.get(
            "/v1/health", headers={"Host": "evil.example"}
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json["error"], "bad_host")

    def test_bad_origin(self) -> None:
        response = self.client.get(
            "/v1/health", headers={"Origin": "https://evil.example"}
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json["error"], "bad_origin")

    def test_origin_port_mismatch(self) -> None:
        response = self.client.get(
            "/v1/health",
            headers={"Origin": "http://127.0.0.1:9999"},
            environ_overrides={"HTTP_HOST": "127.0.0.1:8787"},
        )
        self.assertEqual(response.status_code, 403)

    def test_disabled_pack_is_hidden(self) -> None:
        response = self.client.get("/v1/peer/events")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json["error"], "pack_disabled")
        self.assertEqual(response.json["pack"], "sync")

    def test_unknown_route(self) -> None:
        response = self.client.get("/v1/not-a-route")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json["error"], "not_found")

    def test_write_requires_identity(self) -> None:
        response = self.client.post("/v1/echo", json={"value": 1})
        self.assertEqual(response.status_code, 401)

    def test_write_requires_json(self) -> None:
        response = self.client.post(
            "/v1/echo",
            data="value=1",
            content_type="application/x-www-form-urlencoded",
            headers={"X-Loomsci-Agent": AGENT},
        )
        self.assertEqual(response.status_code, 415)
        self.assertEqual(response.json["error"], "json_required")

    def test_write_with_identity_and_json(self) -> None:
        response = self.client.post(
            "/v1/echo",
            json={"value": 1},
            headers={"X-Loomsci-Agent": AGENT},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["agent"], AGENT)
        self.assertEqual(response.json["echo"], {"value": 1})


if __name__ == "__main__":
    unittest.main()
