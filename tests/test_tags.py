from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import storage  # noqa: E402
from core.app import create_app  # noqa: E402

AGENT = "alice.jiyanjiang"


class TagStorageTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "home"
        self.db = self.home / "data" / "data.db"
        storage.init_db(self.db)
        self.conn = storage.connect(self.db)
        storage.ensure_agent(self.conn, AGENT)

    def tearDown(self) -> None:
        self.conn.close()
        self.tmp.cleanup()

    def test_create_and_filter_tags(self) -> None:
        post = storage.create_post(
            self.conn, author=AGENT, kind="note", body="tagged",
            tags=["Decision", "#architecture", "decision"],
        )
        names = [item["name"] for item in post["tags"]]
        self.assertEqual(names, ["architecture", "decision"])
        self.assertEqual(storage.list_post_tags(self.conn, post_id=post["id"]), post["tags"])
        filtered = storage.list_posts(self.conn, tag="ARCHITECTURE")
        self.assertEqual([item["id"] for item in filtered], [post["id"]])
        self.assertEqual(storage.list_tags(self.conn, limit=10)[0]["count"], 1)

    def test_replace_tags_and_limit(self) -> None:
        post = storage.create_post(self.conn, author=AGENT, kind="note", body="tagged")
        storage.set_post_tags(self.conn, post_id=post["id"], tags=[f"t{i}" for i in range(12)], source="ai")
        tags = storage.list_post_tags(self.conn, post_id=post["id"])
        self.assertEqual(len(tags), 8)
        self.assertTrue(all(item["source"] == "ai" for item in tags))
        storage.set_post_tags(self.conn, post_id=post["id"], tags=["human"], source="human")
        self.assertEqual([item["name"] for item in storage.list_post_tags(self.conn, post_id=post["id"])], ["human"])


class TagApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "home"
        self.app = create_app(env={"LOOMSCI_PROFILE": "core"}, home=self.home)
        conn = storage.connect(self.home / "data" / "data.db")
        storage.ensure_agent(conn, AGENT)
        conn.commit()
        conn.close()
        self.app.testing = True
        self.client = self.app.test_client()
        self.headers = {"X-Loomsci-Agent": AGENT}

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_post_tags_and_cloud(self) -> None:
        created = self.client.post(
            "/v1/posts",
            json={"body": "realistic tag test", "tags": ["decision", "UI"]},
            headers=self.headers,
        )
        self.assertEqual(created.status_code, 201, created.get_data(as_text=True))
        post = created.json["post"]
        self.assertEqual([t["name"] for t in post["tags"]], ["decision", "ui"])
        listed = self.client.get("/v1/posts?tag=decision", headers=self.headers)
        self.assertEqual([p["id"] for p in listed.json["posts"]], [post["id"]])
        cloud = self.client.get("/v1/tags?limit=10", headers=self.headers)
        self.assertEqual(cloud.status_code, 200)
        self.assertEqual([(t["name"], t["count"]) for t in cloud.json["tags"]], [("decision", 1), ("ui", 1)])
        changed = self.client.patch(
            f"/v1/posts/{post['id']}/tags",
            json={"tags": ["architecture"]},
            headers=self.headers,
        )
        self.assertEqual(changed.status_code, 200, changed.get_data(as_text=True))
        self.assertEqual([t["name"] for t in changed.json["tags"]], ["architecture"])


if __name__ == "__main__":
    unittest.main()
