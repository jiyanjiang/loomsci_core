from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import storage, storage_ops  # noqa: E402
from core.home import ensure_layout  # noqa: E402


class StorageOpsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "home"
        self.layout = ensure_layout(self.home)
        storage.init_db(self.layout.db)
        conn = storage.connect(self.layout.db)
        try:
            self.first = storage.add_attachment(
                conn, filename="one.bin", content_type="application/octet-stream",
                data=b"duplicate-content", blob_dir=self.layout.blobs,
            )
            self.second = storage.add_attachment(
                conn, filename="two.bin", content_type="application/octet-stream",
                data=b"duplicate-content", blob_dir=self.layout.blobs,
            )
            self.third = storage.add_attachment(
                conn, filename="three.bin", content_type="application/octet-stream",
                data=b"unique-content", blob_dir=self.layout.blobs,
            )
        finally:
            conn.close()
        (self.layout.blobs / "orphan").write_bytes(b"orphan-content")
        (self.home / "logs").mkdir(exist_ok=True)
        (self.home / "logs" / "app.log").write_bytes(b"log")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_attachment_provenance(self) -> None:
        conn = storage.connect(self.layout.db)
        try:
            item = storage.get_attachment(conn, self.first["id"])
            self.assertEqual(json.loads(item["meta_json"]), {})
            updated = storage.update_attachment_meta(
                conn, self.first["id"],
                {"origin": "generated", "asset_kind": "image", "rights": "owned"},
            )
            self.assertEqual(json.loads(updated["meta_json"])["origin"], "generated")
        finally:
            conn.close()

    def test_report_and_duplicates(self) -> None:
        result = storage_ops.report(self.home)
        self.assertEqual(result["attachments"]["count"], 3)
        self.assertEqual(result["duplicates"]["groups_count"], 1)
        self.assertEqual(result["duplicates"]["groups"][0]["count"], 2)
        self.assertEqual(result["orphans"]["count"], 1)
        self.assertGreater(result["reclaimable_bytes"], 0)
        self.assertGreaterEqual(result["logs_bytes"], 3)
        dup = storage_ops.duplicates(self.home)
        self.assertEqual(dup["groups_count"], 1)

    def test_dedupe_and_prune_apply(self) -> None:
        dry = storage_ops.dedupe(self.home)
        self.assertFalse(dry["apply"])
        self.assertEqual(dry["replaced"], 1)
        self.assertTrue((self.layout.blobs / self.first["id"]).is_file())
        applied = storage_ops.dedupe(self.home, apply=True)
        self.assertTrue(applied["apply"])
        self.assertTrue(os.path.samefile(
            self.layout.blobs / self.first["id"],
            self.layout.blobs / self.second["id"],
        ))
        after = storage_ops.report(self.home)
        self.assertEqual(after["duplicates"]["reclaimable_bytes"], 0)
        prune = storage_ops.prune(self.home, apply=False, older_than=0)
        self.assertEqual(len(prune["candidates"]), 1)
        self.assertTrue((self.layout.blobs / "orphan").is_file())
        removed = storage_ops.prune(self.home, apply=True, older_than=0)
        self.assertEqual(removed["removed"], 1)
        self.assertFalse((self.layout.blobs / "orphan").exists())
        self.assertTrue((self.layout.blobs / self.third["id"]).is_file())

    def test_compact_dry_run(self) -> None:
        result = storage_ops.compact(self.home)
        self.assertTrue(result["ok"])
        self.assertFalse(result["apply"])


if __name__ == "__main__":
    unittest.main()
