from __future__ import annotations

import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import alice, export, storage  # noqa: E402


class ExportTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "source"
        self.db_path = self.home / "data" / "data.db"
        storage.init_db(self.db_path)
        self.conn = storage.connect(self.db_path)
        alice.ensure(self.home, "owner")
        storage.ensure_agent(self.conn, "alice.owner")
        storage.create_post(
            self.conn,
            author="alice.owner",
            kind="note",
            title="Hello",
            body="export me",
        )
        storage.create_task(
            self.conn, title="Do work", description="d", acceptance="a"
        )
        storage.upsert_presence(
            self.conn,
            agent="alice.owner",
            tool="workbuddy",
            workspace="project",
        )
        self.conn.close()
        (self.home / "agents" / "alice" / ".key").write_text("secret", encoding="utf-8")
        (self.home / "data" / "blobs").mkdir(parents=True, exist_ok=True)
        (self.home / "data" / "blobs" / "abc").write_bytes(b"blob")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_roundtrip_counts_and_files(self) -> None:
        out = Path(self.tmp.name) / "export.zip"
        result = export.export_home(self.home, out)
        self.assertEqual(result["counts"]["posts"], 1)
        self.assertEqual(result["counts"]["tasks"], 1)
        with zipfile.ZipFile(out) as zf:
            names = zf.namelist()
            self.assertIn("manifest.json", names)
            self.assertIn("data.json", names)
            self.assertIn("agents/alice/persona.yaml", names)
            self.assertIn("blobs/abc", names)
            self.assertNotIn("agents/alice/.key", names)

        destination = Path(self.tmp.name) / "destination"
        imported = export.import_home(out, destination)
        self.assertEqual(imported["counts"]["posts"], 1)
        self.assertEqual(imported["counts"]["tasks"], 1)
        self.assertTrue((destination / "agents" / "alice" / "persona.yaml").is_file())
        self.assertTrue((destination / "data" / "blobs" / "abc").is_file())
        self.assertTrue((destination / "data" / "data.db").is_file())

    def test_unsafe_member_rejected(self) -> None:
        bad = Path(self.tmp.name) / "bad.zip"
        with zipfile.ZipFile(bad, "w") as zf:
            zf.writestr("../evil.txt", "x")
        with self.assertRaises(export.ExportError):
            export.import_home(bad, Path(self.tmp.name) / "dest")

    def test_sensitive_member_rejected(self) -> None:
        bad = Path(self.tmp.name) / "bad-key.zip"
        with zipfile.ZipFile(bad, "w") as zf:
            zf.writestr("agents/alice/.key", "secret")
        with self.assertRaises(export.ExportError):
            export.import_home(bad, Path(self.tmp.name) / "dest2")


if __name__ == "__main__":
    unittest.main()
