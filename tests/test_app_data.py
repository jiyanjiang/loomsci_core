from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import alice  # noqa: E402
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

    def test_read_cursor(self) -> None:
        set_cursor = self.client.post(
            "/v1/read",
            json={"scope": "posts", "last_seq": 7},
            headers=self.headers,
        )
        self.assertEqual(set_cursor.status_code, 200)
        got = self.client.get("/v1/read?scope=posts", headers=self.headers)
        self.assertEqual(got.status_code, 200)
        self.assertEqual(got.json["cursor"], 7)

    def test_presence(self) -> None:
        registered = self.client.post(
            "/v1/presence",
            json={"tool": "workbuddy", "workspace": "project", "model": "m"},
            headers=self.headers,
        )
        self.assertEqual(registered.status_code, 200)
        listed = self.client.get("/v1/presence", headers=self.headers)
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json["presence"][0]["tool"], "workbuddy")

    def test_handoff(self) -> None:
        created = self.client.post(
            "/v1/tasks", json={"title": "Handoff work"}, headers=self.headers
        )
        task_id = created.json["task"]["id"]
        response = self.client.post(
            "/v1/handoff",
            json={
                "task_id": task_id,
                "to": OTHER,
                "completed": ["schema"],
                "remaining": ["tests"],
                "next": ["run tests"],
                "risks": ["none"],
                "evidence": {"command": "pytest", "exit": 0},
            },
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 201, response.get_data(as_text=True))
        post = response.json["post"]
        self.assertEqual(post["kind"], "handoff")
        self.assertEqual(post["meta"]["to"], OTHER)
        self.assertIn("Handoff", post["body"])

    def test_handoff_requires_evidence(self) -> None:
        created = self.client.post(
            "/v1/tasks", json={"title": "Handoff work"}, headers=self.headers
        )
        task_id = created.json["task"]["id"]
        response = self.client.post(
            "/v1/handoff",
            json={"task_id": task_id, "to": OTHER},
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 400)

    def test_handoff_unknown_task(self) -> None:
        response = self.client.post(
            "/v1/handoff",
            json={"task_id": "t-missing", "to": OTHER, "evidence": "x"},
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 404)

    def test_data_pages_are_read_only_public(self) -> None:
        self.client.post(
            "/v1/posts",
            json={"kind": "note", "title": "Visible", "body": "hello"},
            headers=self.headers,
        )
        self.client.post(
            "/v1/tasks",
            json={"title": "Visible task", "acceptance": "ok"},
            headers=self.headers,
        )
        posts = self.client.get("/app/posts")
        self.assertEqual(posts.status_code, 200)
        self.assertIn("Visible", posts.get_data(as_text=True))
        tasks = self.client.get("/app/tasks")
        self.assertEqual(tasks.status_code, 200)
        self.assertIn("Visible task", tasks.get_data(as_text=True))

    def test_memory_api_and_review(self) -> None:
        created = self.client.post(
            "/v1/memory",
            json={
                "claim": "hello.md exists",
                "evidence": "sha256 matches",
                "source": "test",
            },
            headers=self.headers,
        )
        self.assertEqual(created.status_code, 201, created.get_data(as_text=True))
        fact_id = created.json["fact"]["id"]
        self.assertEqual(created.json["fact"]["status"], "candidate")
        listed = self.client.get("/v1/memory?q=hello", headers=self.headers)
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.json["facts"]), 1)
        reviewed = self.client.post(
            f"/v1/memory/{fact_id}/review",
            json={"status": "approved"},
            headers=self.headers,
        )
        self.assertEqual(reviewed.status_code, 200)
        self.assertEqual(reviewed.json["fact"]["status"], "approved")

    def test_ui_write_and_memory_page(self) -> None:
        alice.ensure(self.home, "owner")
        posted = self.client.post(
            "/app/posts",
            data={"title": "UI post", "body": "from form"},
        )
        self.assertEqual(posted.status_code, 302)
        self.assertIn("UI post", self.client.get("/app/posts").get_data(as_text=True))
        task = self.client.post(
            "/app/tasks",
            data={"title": "UI task", "acceptance": "ok"},
        )
        self.assertEqual(task.status_code, 302)
        self.assertIn("UI task", self.client.get("/app/tasks").get_data(as_text=True))
        fact = self.client.post(
            "/v1/memory",
            json={"claim": "UI fact", "evidence": "form"},
            headers=self.headers,
        )
        fact_id = fact.json["fact"]["id"]
        self.assertIn("UI fact", self.client.get("/app/memory").get_data(as_text=True))
        review = self.client.post(
            f"/app/memory/{fact_id}/review",
            data={"status": "approved"},
        )
        self.assertEqual(review.status_code, 302)
        self.assertIn("UI fact", self.client.get("/app/memory").get_data(as_text=True))

    def test_database_is_created_in_home(self) -> None:
        self.assertTrue((self.home / "data" / "data.db").is_file())


if __name__ == "__main__":
    unittest.main()
