from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import storage, updates  # noqa: E402
from core.app import create_app  # noqa: E402


class SecurityBoundaryTest(unittest.TestCase):
    def setUp(self) -> None:
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

    def test_health_is_public(self) -> None:
        self.assertEqual(self.client.get("/v1/health").status_code, 200)

    def test_host_must_be_loopback(self) -> None:
        response = self.client.get("/v1/health", headers={"Host": "evil.example"})
        self.assertEqual(response.status_code, 403)

    def test_cross_origin_write_is_rejected(self) -> None:
        response = self.client.post(
            "/v1/posts",
            json={"body": "x"},
            headers={**self.headers, "Origin": "http://evil.example"},
        )
        self.assertEqual(response.status_code, 403)

    def test_writes_require_json(self) -> None:
        response = self.client.post(
            "/v1/posts",
            data="body=x",
            headers=self.headers,
            content_type="application/x-www-form-urlencoded",
        )
        self.assertEqual(response.status_code, 415)

    def test_writes_require_agent(self) -> None:
        response = self.client.post("/v1/posts", json={"body": "x"})
        self.assertEqual(response.status_code, 401)

    def test_update_write_requires_agent(self) -> None:
        self.assertEqual(self.client.post("/v1/update/check").status_code, 401)


class UpdateSecurityTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "home"
        (self.home / "core").mkdir(parents=True)
        (self.home / "core" / "VERSION").write_text("1.0.0", encoding="utf-8")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_non_https_remote_update_url_is_rejected(self) -> None:
        with self.assertRaises(updates.UpdateError):
            updates._validate_url("http://example.com/latest.json", label="update")
        with self.assertRaises(updates.UpdateError):
            updates._validate_url("file:///tmp/latest.json", label="update")
        self.assertEqual(
            updates._validate_url("http://127.0.0.1:8000/latest.json", label="update"),
            "http://127.0.0.1:8000/latest.json",
        )

    def test_tampered_download_is_rejected(self) -> None:
        package = self.home / "updates" / "release.zip"
        package.parent.mkdir(parents=True)
        package.write_bytes(b"tampered")
        (self.home / "runtime").mkdir()
        (self.home / "runtime" / "update.json").write_text(json.dumps({
            "downloaded": {"path": str(package), "sha256": "0" * 64, "bytes": 8}
        }), encoding="utf-8")
        with self.assertRaises(updates.UpdateError):
            updates.verify_downloaded(self.home)


if __name__ == "__main__":
    unittest.main()
