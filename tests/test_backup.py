from __future__ import annotations

import sys
import tempfile
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
            )
            second = storage.add_attachment(
                conn, filename="copy.png", content_type="image/png",
                data=PNG, blob_dir=self.layout.blobs,
            )
            storage.add_attachment(
                conn, filename="paper.pdf", content_type="application/pdf",
                data=b"%PDF-1.4 reference", blob_dir=self.layout.blobs,
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
