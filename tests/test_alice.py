from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import alice, storage  # noqa: E402


class AliceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "home"
        self.db = self.home / "data" / "data.db"
        storage.init_db(self.db)
        self.conn = storage.connect(self.db)

    def tearDown(self) -> None:
        self.conn.close()
        self.tmp.cleanup()

    def test_baseline_has_no_private_dimensions(self) -> None:
        persona = alice.baseline_persona()
        self.assertNotIn("body", persona)
        self.assertNotIn("wardrobe", persona)
        self.assertEqual(persona["autonomy"]["default"], "ask_before_irreversible")

    def test_ensure_creates_baseline_files(self) -> None:
        record = alice.ensure(self.home, "owner")
        self.assertEqual(record["handle"], "alice.owner")
        directory = self.home / "agents" / "alice"
        self.assertTrue((directory / "agent.json").is_file())
        self.assertTrue((directory / "persona.yaml").is_file())
        self.assertTrue((directory / "adapters" / "codex.md").is_file())
        instructions = (directory / "instructions.md").read_text(encoding="utf-8")
        self.assertIn("alice.owner", instructions)
        self.assertNotIn("{{HANDLE}}", instructions)
        self.assertEqual(alice.ensure(self.home, "owner")["handle"], "alice.owner")

    def test_rename_records_history_and_alias(self) -> None:
        storage.ensure_agent(self.conn, "alice.owner")
        alice.ensure(self.home, "owner")
        record = alice.rename(self.home, self.conn, "alice", "assistant")
        self.assertEqual(record["handle"], "assistant.owner")
        self.assertTrue((self.home / "agents" / "assistant" / "agent.json").is_file())
        history = json.loads(
            (self.home / "agents" / "assistant" / "renames.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(history[0]["from"], "alice.owner")
        self.assertEqual(storage.resolve_handle(self.conn, "alice.owner"), "assistant.owner")

    def test_snapshot_and_review(self) -> None:
        alice.ensure(self.home, "owner")
        path = alice.snapshot(self.home, "alice", "test")
        self.assertTrue(path.is_file())
        self.assertNotIn(":", path.name)
        review = alice.review(self.home, "alice")
        self.assertEqual(len(review["versions"]), 1)

    def test_reset_keeps_memory(self) -> None:
        alice.ensure(self.home, "owner")
        memory = self.home / "agents" / "alice" / "memory.db"
        memory.write_bytes(b"memory")
        alice.reset(self.home, "alice", keep_memory=True)
        self.assertTrue(memory.is_file())
        self.assertTrue(
            (self.home / "agents" / "alice" / "versions").is_dir()
        )


if __name__ == "__main__":
    unittest.main()
