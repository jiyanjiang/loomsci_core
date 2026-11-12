#!/usr/bin/env python3
"""Create a temporary 10k/50k dataset and report FTS5 search latency."""

from __future__ import annotations

import argparse
import json
import statistics
import tempfile
import time
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import storage


def run(posts: int, facts: int, query: str, rounds: int) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "data.db"
        storage.init_db(db)
        conn = storage.connect(db)
        try:
            conn.executemany(
                "INSERT INTO posts(id, author, kind, body, created_at) VALUES (?,?,?,?,?)",
                [(f"p-{i}", "bench", "note", f"ordinary body {i}", "2026-01-01") for i in range(posts)]
                + [("p-needle", "bench", "note", "unique needle phrase", "2026-01-02")],
            )
            conn.executemany(
                "INSERT INTO facts(id, claim, status, created_at, updated_at) VALUES (?,?,?,?,?)",
                [(f"f-{i}", f"ordinary claim {i}", "candidate", "2026-01-01", "2026-01-01") for i in range(facts)]
                + [("f-needle", "unique needle fact", "candidate", "2026-01-01", "2026-01-01")],
            )
            conn.commit()
            times = []
            for _ in range(rounds):
                started = time.perf_counter()
                result = storage.search(conn, q=query, limit=50)
                times.append((time.perf_counter() - started) * 1000)
            times.sort()
            return {
                "posts": posts,
                "facts": facts,
                "query": query,
                "rounds": rounds,
                "results": len(result),
                "p50_ms": round(statistics.median(times), 2),
                "p95_ms": round(times[min(len(times) - 1, int(len(times) * 0.95))], 2),
                "max_ms": round(max(times), 2),
            }
        finally:
            conn.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--posts", type=int, default=10_000)
    parser.add_argument("--facts", type=int, default=50_000)
    parser.add_argument("--query", default="needle")
    parser.add_argument("--rounds", type=int, default=20)
    args = parser.parse_args()
    print(json.dumps(run(args.posts, args.facts, args.query, args.rounds), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
