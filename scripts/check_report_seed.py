#!/usr/bin/env python3
"""Acceptance check for the Report seed library."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "report" / "report_seed.db"


def main() -> int:
    if not DB.is_file():
        raise SystemExit(f"missing {DB}; run scripts/build_report_seed.py")
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    try:
        total = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
        oa = conn.execute("SELECT COUNT(*) FROM articles WHERE oa_status=1").fetchone()[0]
        cc = conn.execute(
            "SELECT COUNT(*) FROM articles WHERE oa_status=1 AND license LIKE 'cc-%'"
        ).fetchone()[0]
        full = conn.execute(
            "SELECT COUNT(*) FROM articles WHERE oa_status=1 "
            "AND (full_text_url != '' OR pdf_url != '')"
        ).fetchone()[0]
        matched = conn.execute(
            "SELECT COUNT(DISTINCT left_id) FROM article_matches"
        ).fetchone()[0]
        unique_doi = conn.execute("SELECT COUNT(DISTINCT doi) FROM articles").fetchone()[0]
        missing = conn.execute(
            "SELECT COUNT(*) FROM articles WHERE doi='' OR title=''"
        ).fetchone()[0]
        checks = {
            "total_nature_perspectives": total,
            "oa": oa,
            "cc_license": cc,
            "oa_full_text_url": full,
            "matched_pmc_or_arxiv": matched,
            "unique_doi": unique_doi,
            "missing_doi_or_title": missing,
            "pass": (
                total >= 10
                and oa >= 10
                and cc >= 10
                and full >= 10
                and matched >= 5
                and unique_doi == total
                and missing == 0
            ),
        }
        print(json.dumps(checks, ensure_ascii=False, indent=2))
        return 0 if checks["pass"] else 1
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
