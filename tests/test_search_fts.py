from __future__ import annotations

import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import storage  # noqa: E402


class FtsSearchTest(unittest.TestCase):
    def test_fts_indexes_and_searches_large_dataset(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "data.db"
            storage.init_db(db)
            conn = storage.connect(db)
            try:
                rows = [
                    (f"p-{i}", "alice", "note", f"ordinary body {i}", "2026-01-01")
                    for i in range(10_000)
                ]
                rows.append(("p-needle", "alice", "note", "unique needle phrase", "2026-01-02"))
                conn.executemany(
                    "INSERT INTO posts(id, author, kind, body, created_at) VALUES (?,?,?,?,?)",
                    rows,
                )
                facts = [
                    (f"f-{i}", f"claim {i}", "candidate", "2026-01-01", "2026-01-01")
                    for i in range(50_000)
                ]
                facts.append(("f-needle", "unique needle fact", "candidate", "2026-01-01", "2026-01-01"))
                conn.executemany(
                    "INSERT INTO facts(id, claim, status, created_at, updated_at) VALUES (?,?,?,?,?)",
                    facts,
                )
                conn.commit()
                started = time.monotonic()
                results = storage.search(conn, q="needle", limit=20)
                elapsed = time.monotonic() - started
                self.assertTrue(any(item["id"] == "p-needle" for item in results))
                self.assertTrue(any(item["id"] == "f-needle" for item in results))
                self.assertLess(elapsed, 2.0)
            finally:
                conn.close()

    def test_fts_tracks_update_and_delete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "data.db"
            storage.init_db(db)
            conn = storage.connect(db)
            try:
                post = storage.create_post(conn, author="alice", kind="note", body="alpha")
                self.assertTrue(storage.search(conn, q="alpha"))
                conn.execute("UPDATE posts SET body='beta' WHERE id=?", (post["id"],))
                conn.commit()
                self.assertFalse(storage.search(conn, q="alpha"))
                self.assertTrue(storage.search(conn, q="beta"))
                conn.execute("DELETE FROM posts WHERE id=?", (post["id"],))
                conn.commit()
                self.assertFalse(storage.search(conn, q="beta"))
            finally:
                conn.close()


if __name__ == "__main__":
    unittest.main()
