from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.app import create_app  # noqa: E402

AGENT = "alice.jiyanjiang"
OTHER = "bob.jiyanjiang"


class AppDataTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "home"
        self.app = create_app(
            env={"LOOMSCI_PROFILE": "core"}, home=self.home
        )
        self.app.testing = True
        self.client = self.app.test_client()
        self.headers = {"X-Loomsci-Agent": AGENT}

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_post_roundtrip(self) -> None:
        response = self.client.post(
            "/v1/posts",
            json={"kind": "note", "title": "Hello", "body": "First post"},
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 201, response.get_data(as_text=True))
        self.assertTrue(response.json["post"]["id"].startswith("p-"))

        listed = self.client.get("/v1/posts", headers=self.headers)
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.json["posts"]), 1)
        self.assertEqual(listed.json["posts"][0]["body"], "First post")

    def test_posts_require_identity(self) -> None:
        response = self.client.get("/v1/posts")
        self.assertEqual(response.status_code, 401)

    def test_post_requires_body(self) -> None:
        response = self.client.post(
            "/v1/posts", json={"kind": "note"}, headers=self.headers
        )
        self.assertEqual(response.status_code, 400)

    def test_task_lease_and_done(self) -> None:
        created = self.client.post(
            "/v1/tasks",
            json={"title": "Do work", "acceptance": "tests pass"},
            headers=self.headers,
        )
        self.assertEqual(created.status_code, 201, created.get_data(as_text=True))
        task_id = created.json["task"]["id"]

        claimed = self.client.post(
            f"/v1/tasks/{task_id}/claim", json={}, headers=self.headers
        )
        self.assertEqual(claimed.status_code, 200, claimed.get_data(as_text=True))
        self.assertEqual(claimed.json["task"]["assigned_to"], AGENT)

        conflict = self.client.post(
            f"/v1/tasks/{task_id}/claim",
            json={},
            headers={"X-Loomsci-Agent": OTHER},
        )
        self.assertEqual(conflict.status_code, 409)

        forbidden = self.client.post(
            f"/v1/tasks/{task_id}/done",
            json={"evidence": {"ok": True}},
            headers={"X-Loomsci-Agent": OTHER},
        )
        self.assertEqual(forbidden.status_code, 403)

        done = self.client.post(
            f"/v1/tasks/{task_id}/done",
            json={"evidence": {"command": "python -m unittest", "exit": 0}},
            headers=self.headers,
        )
        self.assertEqual(done.status_code, 200, done.get_data(as_text=True))
        self.assertEqual(done.json["task"]["status"], "done")

    def test_done_requires_evidence(self) -> None:
        created = self.client.post(
            "/v1/tasks", json={"title": "Do work"}, headers=self.headers
        )
        task_id = created.json["task"]["id"]
        self.client.post(
            f"/v1/tasks/{task_id}/claim", json={}, headers=self.headers
        )
        response = self.client.post(
            f"/v1/tasks/{task_id}/done", json={}, headers=self.headers
        )
        self.assertEqual(response.status_code, 400)

    def test_database_is_created_in_home(self) -> None:
        self.assertTrue((self.home / "data" / "data.db").is_file())


if __name__ == "__main__":
    unittest.main()
