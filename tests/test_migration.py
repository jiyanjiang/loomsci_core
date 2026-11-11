from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import backup, migration, storage  # noqa: E402
from core.home import ensure_layout  # noqa: E402


class MigrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.source = Path(self.tmp.name) / "source"
        layout = ensure_layout(self.source)
        storage.init_db(layout.db)
        conn = storage.connect(layout.db)
        try:
            storage.create_post(conn, author="alice.old", kind="note", body="old workspace")
            storage.add_attachment(
                conn, filename="generated.pdf", content_type="application/pdf",
                data=b"%PDF generated", blob_dir=layout.blobs,
                meta={"origin": "generated", "asset_kind": "document", "rights": "owned"},
            )
        finally:
            conn.close()
        (self.source / "agents" / "alice.old").mkdir(parents=True)
        (self.source / "agents" / "alice.old" / "agent.json").write_text('{"handle":"alice.old"}')
        self.bundle = Path(self.tmp.name) / "workspace.zip"
        backup.create(self.source, self.bundle)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _target(self) -> Path:
        target = Path(self.tmp.name) / "target"
        layout = ensure_layout(target)
        storage.init_db(layout.db)
        conn = storage.connect(layout.db)
        try:
            storage.ensure_agent(conn, "alice.new")
            conn.commit()
        finally:
            conn.close()
        (target / "agents" / "alice.new").mkdir(parents=True)
        (target / "agents" / "alice.new" / ".key").write_text("local-key")
        (target / "config.yaml").write_text("llm:\n  deepseek_api_key: local-secret\n")
        (target / "core").mkdir()
        return target

    def test_empty_installed_target_imports(self) -> None:
        target = self._target()
        self.assertEqual(migration.state(target)["state"], "empty")
        dry = migration.import_bundle(self.bundle, target)
        self.assertTrue(dry["dry_run"])
        applied = migration.import_bundle(self.bundle, target, apply=True)
        self.assertFalse(applied["dry_run"])
        self.assertEqual(applied["state_after"]["state"], "used")
        self.assertIn("alice.new", applied["preserved_agents"])
        self.assertEqual(
            (target / "runtime" / "pre-import-agents" / "alice.new" / ".key").read_text(),
            "local-key",
        )
        self.assertIn("local-secret", (target / "config.yaml").read_text())
        conn = storage.connect(target / "data" / "data.db")
        try:
            self.assertEqual(conn.execute("SELECT count(*) FROM posts").fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT count(*) FROM attachments").fetchone()[0], 1)
        finally:
            conn.close()

    def test_used_target_is_refused(self) -> None:
        target = self._target()
        conn = storage.connect(target / "data" / "data.db")
        try:
            storage.create_post(conn, author="alice.new", kind="note", body="already used")
        finally:
            conn.close()
        with self.assertRaises(migration.MigrationError):
            migration.import_bundle(self.bundle, target, apply=True)


if __name__ == "__main__":
    unittest.main()
