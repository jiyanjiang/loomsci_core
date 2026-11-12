from __future__ import annotations

import sys
import tempfile
import unittest
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import upgrade  # noqa: E402
from core import storage  # noqa: E402


class UpgradeMatrixTest(unittest.TestCase):
    def test_old_packages_swap_preserve_data_and_rollback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            (home / "data").mkdir(parents=True)
            marker = b"legacy-database"
            (home / "data" / "data.db").write_bytes(marker)
            for version in ("1", "6", "9"):
                package = ROOT / "releases" / f"loomsci_core-0.1.0-beta.{version}.zip"
                self.assertTrue(package.is_file(), package)
                result = upgrade.apply(package, home, backup=False)
                self.assertTrue(result["ok"])
                self.assertEqual((home / "core" / "VERSION").read_text().strip(), f"0.1.0-beta.{version}")
                self.assertEqual((home / "data" / "data.db").read_bytes(), marker)
                if version != "1":
                    self.assertTrue((home / "core.prev").is_dir())
            final = ROOT / "releases" / "loomsci_core-0.1.0-beta.12.zip"
            upgrade.apply(final, home, backup=False)
            self.assertEqual((home / "core" / "VERSION").read_text().strip(), "0.1.0-beta.12")
            self.assertEqual((home / "data" / "data.db").read_bytes(), marker)
            upgrade.rollback(home)
            self.assertEqual((home / "core" / "VERSION").read_text().strip(), "0.1.0-beta.9")
            self.assertEqual((home / "data" / "data.db").read_bytes(), marker)

    def test_large_legacy_database_migrates_without_loss(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "data" / "data.db"
            db.parent.mkdir(parents=True)
            conn = sqlite3.connect(db)
            conn.execute(
                "CREATE TABLE posts (seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT UNIQUE, "
                "thread_id TEXT, parent_id TEXT, author TEXT, kind TEXT, title TEXT, "
                "body TEXT NOT NULL, meta_json TEXT, created_at TEXT NOT NULL)"
            )
            conn.execute(
                "CREATE TABLE facts (id TEXT PRIMARY KEY, project TEXT, claim TEXT NOT NULL, "
                "evidence TEXT, source TEXT, tags TEXT, status TEXT, confidence REAL, "
                "created_by TEXT, reviewed_by TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)"
            )
            conn.executemany(
                "INSERT INTO posts(id, author, kind, title, body, created_at) VALUES (?,?,?,?,?,?)",
                [(f"p-{i}", "alice", "note", "legacy", f"body {i}", "2026-01-01") for i in range(10_000)],
            )
            conn.executemany(
                "INSERT INTO facts(id, claim, status, created_at, updated_at) VALUES (?,?,?,?,?)",
                [(f"f-{i}", f"claim {i}", "candidate", "2026-01-01", "2026-01-01") for i in range(50_000)],
            )
            conn.commit()
            conn.close()
            storage.init_db(db)
            conn = storage.connect(db)
            try:
                counts = storage.stats(conn)["counts"]
                self.assertEqual(counts["posts"], 10_000)
                self.assertEqual(counts["facts"], 50_000)
                columns = {row[1] for row in conn.execute("PRAGMA table_info(posts)")}
                self.assertNotIn("title", columns)
            finally:
                conn.close()


if __name__ == "__main__":
    unittest.main()
