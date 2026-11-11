from __future__ import annotations

import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import llm_config  # noqa: E402


class LlmConfigTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "home"
        self.home.mkdir()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_legacy_key_is_read_and_not_returned_publicly(self) -> None:
        (self.home / "config.yaml").write_text(
            "llm:\n  deepseek_api_key: legacy-key\n", encoding="utf-8"
        )
        self.assertEqual(llm_config.get_key(self.home, "deepseek"), "legacy-key")
        public = llm_config.public(self.home, "deepseek")
        self.assertTrue(public["configured"])
        self.assertNotIn("legacy-key", str(public))

    def test_save_migrates_and_limits_permissions(self) -> None:
        (self.home / "config.yaml").write_text(
            "llm:\n  deepseek_api_key: old\n", encoding="utf-8"
        )
        llm_config.set_key(self.home, "deepseek", "new-key")
        text = (self.home / "config.yaml").read_text(encoding="utf-8")
        self.assertIn("new-key", text)
        self.assertNotIn("deepseek_api_key", text)
        if os.name != "nt":
            mode = stat.S_IMODE((self.home / "config.yaml").stat().st_mode)
            self.assertEqual(mode & 0o077, 0)
        self.assertEqual(llm_config.get_key(self.home, "deepseek"), "new-key")
        llm_config.set_key(self.home, "deepseek", "")
        self.assertFalse(llm_config.public(self.home, "deepseek")["configured"])

    def test_provider_fields(self) -> None:
        result = llm_config.set_fields(
            self.home, "deepseek", base_url="https://example.test", model="m"
        )
        self.assertEqual(result["base_url"], "https://example.test")
        self.assertEqual(result["model"], "m")
        self.assertFalse(result["configured"])


class SettingsApiTest(unittest.TestCase):
    def setUp(self) -> None:
        from core import storage
        from core.app import create_app

        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "home"
        self.app = create_app(env={"LOOMSCI_PROFILE": "core"}, home=self.home)
        conn = storage.connect(self.home / "data" / "data.db")
        storage.ensure_agent(conn, "alice.test")
        conn.commit()
        conn.close()
        self.app.testing = True
        self.client = self.app.test_client()
        self.headers = {"X-Loomsci-Agent": "alice.test"}

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_key_roundtrip_never_returns_secret(self) -> None:
        response = self.client.put(
            "/v1/settings/llm/deepseek/key",
            json={"api_key": "sk-secret"},
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("sk-secret", response.get_data(as_text=True))
        loaded = self.client.get("/v1/settings/llm/deepseek", headers=self.headers)
        self.assertTrue(loaded.json["provider"]["configured"])
        self.assertNotIn("sk-secret", loaded.get_data(as_text=True))
        cleared = self.client.put(
            "/v1/settings/llm/deepseek/key", json={"api_key": ""}, headers=self.headers
        )
        self.assertFalse(cleared.json["provider"]["configured"])


if __name__ == "__main__":
    unittest.main()
