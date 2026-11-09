from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import storage  # noqa: E402


class StorageTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "data" / "data.db"
        storage.init_db(self.db_path)
        self.conn = storage.connect(self.db_path)

    def tearDown(self) -> None:
        self.conn.close()
        self.tmp.cleanup()

    def test_post_roundtrip(self) -> None:
        post = storage.create_post(
            self.conn,
            author="alice.jiyanjiang",
            kind="note",
            title="Hello",
            body="First post",
            meta={"tag": "test"},
        )
        self.assertTrue(post["id"].startswith("p-"))
        posts = storage.list_posts(self.conn, since=0)
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0]["author"], "alice.jiyanjiang")
        self.assertEqual(posts[0]["meta"], {"tag": "test"})
        self.assertEqual(storage.list_posts(self.conn, since=post["seq"]), [])

    def test_mentions_inbox_and_search(self) -> None:
        post = storage.create_post(
            self.conn,
            author="alice.jiyanjiang",
            kind="ask",
            title="Need review",
            body="Please check @bob.jiyanjiang and @carol.jiyanjiang",
        )
        self.assertEqual(
            post["mentions"], ["bob.jiyanjiang", "carol.jiyanjiang"]
        )
        inbox = storage.list_inbox(self.conn, agent="bob.jiyanjiang")
        self.assertEqual(len(inbox), 1)
        self.assertIsNone(inbox[0]["mention_read_at"])
        self.assertEqual(storage.mark_inbox_read(
            self.conn, agent="bob.jiyanjiang", post_id=post["id"]
        ), 1)
        self.assertEqual(
            storage.list_inbox(self.conn, agent="bob.jiyanjiang", unread_only=True),
            [],
        )
        self.assertEqual(len(storage.search(self.conn, q="review")), 1)
        self.assertEqual(storage.stats(self.conn)["integrity"], "ok")

    def test_attachment_roundtrip(self) -> None:
        post = storage.create_post(
            self.conn, author="alice.jiyanjiang", kind="note", body="with file"
        )
        attachment = storage.add_attachment(
            self.conn,
            filename="note.txt",
            content_type="text/plain",
            data=b"hello",
            blob_dir=Path(self.tmp.name) / "data" / "blobs",
        )
        storage.attach_to_post(
            self.conn, attachment_id=attachment["id"], post_id=post["id"]
        )
        self.assertEqual(len(storage.list_attachments(self.conn, post_id=post["id"])), 1)
        self.assertTrue(
            (Path(self.tmp.name) / "data" / "blobs" / attachment["id"]).is_file()
        )

    def test_invalid_post_kind(self) -> None:
        with self.assertRaises(ValueError):
            storage.create_post(
                self.conn, author="alice.jiyanjiang", kind="unknown", body="x"
            )

    def test_task_claim_conflict_and_done(self) -> None:
        task = storage.create_task(
            self.conn,
            title="Do work",
            description="d",
            acceptance="a",
        )
        claimed = storage.claim_task(
            self.conn, task_id=task["id"], agent="alice.jiyanjiang"
        )
        self.assertEqual(claimed["status"], "claimed")
        self.assertEqual(claimed["assigned_to"], "alice.jiyanjiang")

        with self.assertRaises(storage.Conflict):
            storage.claim_task(self.conn, task_id=task["id"], agent="bob.jiyanjiang")

        with self.assertRaises(storage.Forbidden):
            storage.done_task(
                self.conn,
                task_id=task["id"],
                agent="bob.jiyanjiang",
                evidence={"ok": True},
            )

        done = storage.done_task(
            self.conn,
            task_id=task["id"],
            agent="alice.jiyanjiang",
            evidence={"command": "test", "exit": 0},
        )
        self.assertEqual(done["status"], "done")
        self.assertEqual(done["evidence"]["exit"], 0)

    def test_unknown_task(self) -> None:
        with self.assertRaises(storage.NotFound):
            storage.claim_task(self.conn, task_id="t-missing", agent="alice.jiyanjiang")

    def test_database_permissions(self) -> None:
        if os.name != "posix":
            self.skipTest("POSIX mode check")
        self.assertEqual(self.db_path.stat().st_mode & 0o777, 0o600)

    def test_facts(self) -> None:
        fact = storage.add_fact(
            self.conn,
            claim="hello.md exists",
            evidence="sha256 matches",
            source="test",
            project="p",
            created_by="alice.jiyanjiang",
        )
        self.assertEqual(fact["status"], "candidate")
        self.assertEqual(len(storage.list_facts(self.conn, q="hello")), 1)
        reviewed = storage.review_fact(
            self.conn,
            fact_id=fact["id"],
            status="approved",
            reviewer="alice.jiyanjiang",
        )
        self.assertEqual(reviewed["status"], "approved")
        self.assertEqual(
            len(storage.list_facts(self.conn, status="approved")), 1
        )

    def test_presence_and_read_cursor(self) -> None:
        storage.upsert_presence(
            self.conn,
            agent="alice.jiyanjiang",
            tool="workbuddy",
            workspace="project",
            model="m",
        )
        storage.set_read_cursor(
            self.conn, agent="alice.jiyanjiang", scope="posts", last_seq=3
        )
        self.assertEqual(
            storage.get_read_cursor(
                self.conn, agent="alice.jiyanjiang", scope="posts"
            ),
            3,
        )


if __name__ == "__main__":
    unittest.main()
