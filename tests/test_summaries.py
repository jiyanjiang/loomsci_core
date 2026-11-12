from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import storage, summaries  # noqa: E402
from core.app import create_app  # noqa: E402

AGENT = "alice.jiyanjiang"


class SummariesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "home"
        self.db = self.home / "data" / "data.db"
        storage.init_db(self.db)
        self.conn = storage.connect(self.db)
        storage.ensure_agent(self.conn, AGENT)
        self.conn.commit()

    def tearDown(self) -> None:
        self.conn.close()
        self.tmp.cleanup()

    def test_threshold_and_fallback_length(self) -> None:
        self.assertFalse(summaries.needs_summary("x" * summaries.SHORT_POST_MAX))
        self.assertTrue(summaries.needs_summary("x" * (summaries.SHORT_POST_MAX + 1)))
        body = ("第一段讲目标和证据。" * 100) + "最后结论。"
        text = summaries.fallback(body)
        self.assertLessEqual(len(text), summaries.SUMMARY_MAX)
        self.assertGreaterEqual(len(text), summaries.SUMMARY_MIN)

    def test_long_post_gets_fallback_without_key(self) -> None:
        body = "这是一个长文。" * 120
        post = storage.create_post(self.conn, author=AGENT, kind="note", body=body)
        summaries.enqueue_for_post(self.conn, post_id=post["id"], body=body, home=self.home)
        stored = storage.get_post(self.conn, post["id"])
        self.assertEqual(stored["summary"]["status"], "fallback")
        self.assertLessEqual(len(stored["summary"]["text"]), summaries.SUMMARY_MAX)
        self.assertEqual(stored["body_chars"], len(body))

    def test_short_post_has_no_summary(self) -> None:
        post = storage.create_post(self.conn, author=AGENT, kind="note", body="short")
        summaries.enqueue_for_post(self.conn, post_id=post["id"], body=post["body"], home=self.home)
        self.assertNotIn("summary", storage.get_post(self.conn, post["id"]))

    def test_pending_summary_falls_back_without_key(self) -> None:
        body = "这是一个长文。" * 120
        post = storage.create_post(self.conn, author=AGENT, kind="note", body=body)
        summaries.enqueue_for_post(self.conn, post_id=post["id"], body=body, home=self.home)
        self.conn.execute(
            "UPDATE post_summaries SET status='pending' WHERE post_id=?", (post["id"],)
        )
        self.conn.commit()
        self.assertTrue(summaries.generate_one(self.conn, post_id=post["id"], home=self.home))
        self.assertEqual(
            storage.get_post(self.conn, post["id"])["summary"]["status"], "fallback"
        )

    def test_ensure_queues_extractive_fallback_once_after_key(self) -> None:
        from unittest.mock import patch

        body = "这是一个长文。" * 120
        post = storage.create_post(self.conn, author=AGENT, kind="note", body=body)
        summaries.enqueue_for_post(self.conn, post_id=post["id"], body=body, home=self.home)
        self.assertEqual(
            storage.get_post(self.conn, post["id"])["summary"]["status"], "fallback"
        )
        (self.home / "config.yaml").write_text(
            "llm:\n  providers:\n    deepseek:\n      api_key: test-key\n",
            encoding="utf-8",
        )
        posts = [storage.get_post(self.conn, post["id"])]
        self.assertEqual(summaries.ensure_for_posts(self.conn, posts, home=self.home), 1)
        self.assertEqual(summaries.ensure_for_posts(self.conn, posts, home=self.home), 0)
        with patch.object(summaries, "_generate_ai", return_value="摘要内容。" * 80):
            self.assertTrue(summaries.generate_one(self.conn, post_id=post["id"], home=self.home))
        summary = storage.get_post(self.conn, post["id"])["summary"]
        self.assertEqual(summary["status"], "ready")
        self.assertEqual(summary["model"], "deepseek-flash")
        self.assertEqual(summaries.ensure_for_posts(self.conn, posts, home=self.home), 0)

    def test_pending_summary_uses_model_when_key_configured(self) -> None:
        from unittest.mock import patch

        (self.home / "config.yaml").write_text(
            "llm:\n  deepseek_api_key: test-key\n", encoding="utf-8"
        )
        body = "这是一个长文。" * 120
        post = storage.create_post(self.conn, author=AGENT, kind="note", body=body)
        summaries.enqueue_for_post(self.conn, post_id=post["id"], body=body, home=self.home)
        self.conn.execute(
            "UPDATE post_summaries SET status='pending' WHERE post_id=?", (post["id"],)
        )
        self.conn.commit()
        text = "摘要内容。" * 80
        with patch.object(summaries, "_generate_ai", return_value=text):
            self.assertTrue(summaries.generate_one(self.conn, post_id=post["id"], home=self.home))
        summary = storage.get_post(self.conn, post["id"])["summary"]
        self.assertEqual(summary["status"], "ready")
        self.assertEqual(summary["text"], text)


class FeedApiTest(unittest.TestCase):
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
        self.long_body = "# 长文\n\n" + ("证据与结论。" * 200)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_long_post_returns_full_body_in_feed(self) -> None:
        created = self.client.post(
            "/v1/posts", json={"kind": "note", "body": self.long_body}, headers=self.headers
        )
        self.assertEqual(created.status_code, 201, created.get_data(as_text=True))
        post = created.json["post"]
        self.assertNotIn("title", post)
        self.assertNotIn("summary", post)
        feed = self.client.get("/v1/posts?limit=10&view=feed", headers=self.headers).json["posts"]
        self.assertEqual(feed[0]["body"], self.long_body)
        self.assertNotIn("has_more", feed[0])

    def test_short_post_stays_full_in_feed(self) -> None:
        created = self.client.post(
            "/v1/posts", json={"kind": "note", "body": "short body"}, headers=self.headers
        )
        post = created.json["post"]
        self.assertNotIn("summary", post)
        feed = self.client.get("/v1/posts?limit=10&view=feed", headers=self.headers).json["posts"]
        self.assertEqual(feed[0]["body"], "short body")
        self.assertNotIn("has_more", feed[0])


if __name__ == "__main__":
    unittest.main()
