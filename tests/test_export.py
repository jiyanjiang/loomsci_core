from __future__ import annotations

import sys
import tempfile
import unittest
from unittest import mock
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
        post = storage.create_post(
            self.conn,
            author="alice.owner",
            kind="note",
            title="Hello",
            body="export me @bob.owner",
        )
        attachment = storage.add_attachment(
            self.conn,
            filename="note.txt",
            content_type="text/plain",
            data=b"hello",
            blob_dir=self.home / "data" / "blobs",
        )
        storage.attach_to_post(
            self.conn, attachment_id=attachment["id"], post_id=post["id"]
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
        storage.add_fact(
            self.conn,
            claim="project uses python",
            evidence="pyproject.toml",
            source="test",
            created_by="alice.owner",
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
        self.assertEqual(result["counts"]["facts"], 1)
        self.assertEqual(result["counts"]["mentions"], 1)
        self.assertEqual(result["counts"]["attachments"], 1)
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
        self.assertEqual(imported["counts"]["facts"], 1)
        self.assertEqual(imported["counts"]["mentions"], 1)
        self.assertEqual(imported["counts"]["attachments"], 1)
        self.assertTrue((destination / "agents" / "alice" / "persona.yaml").is_file())
        self.assertTrue((destination / "data" / "blobs" / "abc").is_file())
        self.assertTrue((destination / "data" / "data.db").is_file())

    def test_export_temp_is_on_destination_drive(self) -> None:
        out = Path(self.tmp.name) / "out" / "export.zip"
        with mock.patch(
            "core.export.tempfile.mkstemp", wraps=tempfile.mkstemp
        ) as mkstemp:
            export.export_home(self.home, out)
        self.assertEqual(mkstemp.call_args.kwargs["dir"], out.parent)

    def test_corrupt_zip_rejected(self) -> None:
        bad = Path(self.tmp.name) / "corrupt.zip"
        bad.write_bytes(b"not a zip")
        destination = Path(self.tmp.name) / "corrupt-dest"
        with self.assertRaises(export.ExportError):
            export.import_home(bad, destination)
        self.assertFalse(destination.exists())

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
