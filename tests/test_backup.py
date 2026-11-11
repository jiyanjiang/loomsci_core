from __future__ import annotations

import json
import shutil
import sqlite3
import sys
import tempfile
import zipfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import backup, storage  # noqa: E402
from core.home import ensure_layout  # noqa: E402

PNG = b"\x89PNG\r\n\x1a\n" + b"same-bytes" * 8


class BackupInspectTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "home"
        self.layout = ensure_layout(self.home)
        storage.init_db(self.layout.db)
        conn = storage.connect(self.layout.db)
        try:
            first = storage.add_attachment(
                conn, filename="image.png", content_type="image/png",
                data=PNG, blob_dir=self.layout.blobs,
                meta={"origin": "generated", "asset_kind": "image", "rights": "owned"},
            )
            second = storage.add_attachment(
                conn, filename="copy.png", content_type="image/png",
                data=PNG, blob_dir=self.layout.blobs,
                meta={"origin": "generated", "asset_kind": "image", "rights": "owned"},
            )
            storage.add_attachment(
                conn, filename="paper.pdf", content_type="application/pdf",
                data=b"%PDF-1.4 reference", blob_dir=self.layout.blobs,
                meta={"origin": "downloaded", "asset_kind": "document", "rights": "third_party", "source_url": "https://example.test/paper"},
            )
            storage.add_attachment(
                conn, filename="generated-report.pdf", content_type="application/pdf",
                data=b"%PDF-1.4 generated", blob_dir=self.layout.blobs,
                meta={"origin": "generated", "asset_kind": "document", "rights": "owned"},
            )
            secret = "sk-" + "1234567890abcdefghijklmnop"
            storage.create_post(
                conn, author="alice", kind="note", title="note",
                body="key " + secret,
                attachments=[first["id"], second["id"]],
            )
        finally:
            conn.close()
        (self.home / "agents" / "alice").mkdir(parents=True, exist_ok=True)
        (self.home / "agents" / "alice" / "persona.yaml").write_text("name: alice\n")
        (self.home / "agents" / "alice" / ".key").write_text("secret")
        secret = "sk-" + "abcdefghijklmnopqrstuvwx"
        (self.home / "config.yaml").write_text("llm:\n  deepseek_api_key: " + secret + "\n")
        (self.home / "packs" / "ui_shell" / "data").mkdir(parents=True)
        (self.home / "packs" / "ui_shell" / "data" / "site.json").write_text('{"site_name":"x"}')

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_inspect_classifies_and_detects(self) -> None:
        result = backup.inspect(self.home)
        summary = result["summary"]
        self.assertGreaterEqual(summary["assets"]["files"], 3)  # db, 2 images, site
        self.assertEqual(summary["references"]["files"], 1)
        self.assertGreaterEqual(summary["secrets"]["files"], 2)  # .key + config
        self.assertGreaterEqual(summary["secrets"]["hits"], 2)
        self.assertEqual(len(result["duplicates"]), 1)
        self.assertEqual(result["duplicates"][0]["count"], 2)
        self.assertGreater(result["reclaimable_bytes"], 0)
        paths = {item["path"] for item in result["samples"]["assets"]}
        self.assertIn("data/data.db", paths)
        self.assertIn("agents/alice/persona.yaml", paths)
        self.assertIn("packs/ui_shell/data/site.json", paths)
        self.assertIn("data/blobs", "".join(paths))
        reference_paths = {item["path"] for item in result["samples"]["references"]}
        self.assertTrue(any(path.endswith("paper.pdf") or "blobs/" in path for path in reference_paths))

    def test_create_bundle_blocks_secrets_and_restores_assets(self) -> None:
        out = Path(self.tmp.name) / "backup.zip"
        with self.assertRaises(backup.BackupError):
            backup.create(self.home, out)
        result = backup.create(self.home, out, redact=True)
        self.assertTrue(result["ok"])
        self.assertTrue(out.is_file())
        self.assertTrue(result["counts"]["redacted_rows"] >= 1)

        with zipfile.ZipFile(out) as zf:
            names = set(zf.namelist())
            self.assertIn("data/data.db", names)
            self.assertIn("references.json", names)
            self.assertIn("attachments.json", names)
            self.assertFalse(any(name.endswith("paper.pdf") for name in names))
            self.assertTrue(any("generated-report.pdf" in name for name in names))
            references = json.loads(zf.read("references.json"))
            self.assertEqual(references[0]["filename"], "paper.pdf")
            self.assertEqual(references[0]["origin"], "downloaded")
            conn = sqlite3.connect("file:" + str(self.home / "data" / "data.db") + "?mode=ro", uri=True)
            conn.close()
        shown = backup.inspect_bundle(out)
        self.assertTrue(shown["ok"])
        self.assertTrue(shown["redacted"])
        verified = backup.verify_bundle(out)
        self.assertTrue(verified["ok"])
        self.assertEqual(verified["integrity"], "ok")
        self.assertEqual(verified["missing_assets"], [])

        dest = Path(self.tmp.name) / "restored"
        dry = backup.restore_bundle(out, dest)
        self.assertTrue(dry["dry_run"])
        restored = backup.restore_bundle(out, dest, apply=True)
        self.assertFalse(restored["dry_run"])
        self.assertTrue((dest / "data" / "data.db").is_file())
        self.assertTrue((dest / "agents" / "alice" / "persona.yaml").is_file())
        blobs = list((dest / "data" / "blobs").iterdir())
        self.assertEqual(len(blobs), 3)
        conn = sqlite3.connect(dest / "data" / "data.db")
        try:
            attachment_count = conn.execute("SELECT count(*) FROM attachments").fetchone()[0]
            body = conn.execute("SELECT body FROM posts").fetchone()[0]
        finally:
            conn.close()
        self.assertEqual(attachment_count, 3)
        self.assertNotIn("1234567890abcdefghijklmnop", body)
        self.assertIn("[REDACTED]", body)

    def test_generated_media_and_downloaded_media(self) -> None:
        conn = storage.connect(self.layout.db)
        try:
            storage.add_attachment(
                conn, filename="generated.mp3", content_type="audio/mpeg",
                data=b"generated-audio", blob_dir=self.layout.blobs,
                meta={"origin": "generated", "asset_kind": "audio", "rights": "owned"},
            )
            storage.add_attachment(
                conn, filename="downloaded.mp4", content_type="video/mp4",
                data=b"downloaded-video", blob_dir=self.layout.blobs,
                meta={"origin": "downloaded", "asset_kind": "video", "rights": "third_party"},
            )
        finally:
            conn.close()
        out = Path(self.tmp.name) / "media.zip"
        backup.create(self.home, out, redact=True)
        with zipfile.ZipFile(out) as zf:
            names = set(zf.namelist())
            references = json.loads(zf.read("references.json"))
        self.assertTrue(any(name.endswith("generated.mp3") for name in names))
        self.assertFalse(any(name.endswith("downloaded.mp4") for name in names))
        self.assertTrue(any(item["filename"] == "downloaded.mp4" for item in references))

    def test_backup_retention(self) -> None:
        first = Path(self.tmp.name) / "one.zip"
        second = Path(self.tmp.name) / "two.zip"
        backup.create(self.home, first, redact=True)
        shutil.copy2(first, second)
        result = backup.prune_bundles(Path(self.tmp.name), keep=1)
        self.assertFalse(result["apply"])
        self.assertEqual(len(result["candidates"]), 1)
        self.assertTrue(first.exists() and second.exists())
        applied = backup.prune_bundles(Path(self.tmp.name), keep=1, apply=True)
        self.assertEqual(len(applied["removed"]), 1)

    def test_inspect_is_read_only(self) -> None:
        before = {
            str(path): path.read_bytes()
            for path in self.home.rglob("*")
            if path.is_file() and not path.name.startswith("data.db-")
        }
        backup.inspect(self.home)
        after = {
            str(path): path.read_bytes()
            for path in self.home.rglob("*")
            if path.is_file() and not path.name.startswith("data.db-")
        }
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
