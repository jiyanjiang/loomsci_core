#!/usr/bin/env python3
"""Extract aggregate style metrics from open-access PDFs in the Report seed."""

from __future__ import annotations

import json
import re
import sqlite3
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "report" / "report_seed.db"
CACHE = ROOT / "data" / "report" / "style_samples"
OUT = ROOT / "reports" / "report_seed" / "style_metrics.json"

SELECTED = [
    "10.1038/s41567-022-01602-2",
    "10.1038/s41567-020-0834-8",
    "10.1038/s41567-020-0856-2",
    "10.1038/s41567-020-0838-4",
    "10.1038/s41567-018-0342-2",
    "10.1038/s41567-018-0050-y",
    "10.1038/s41567-026-03304-5",
    "10.1038/s41567-025-03143-w",
    "10.1038/s41567-022-01770-1",
    "10.1038/s41567-022-01666-0",
]


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as response:
        return response.read()


def _safe_name(doi: str) -> str:
    return doi.replace("/", "_").replace(".", "_")


def main() -> int:
    import fitz  # PyMuPDF

    if not DB.is_file():
        raise SystemExit("seed DB missing")
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    CACHE.mkdir(parents=True, exist_ok=True)
    rows = []
    for doi in SELECTED:
        row = conn.execute(
            "SELECT doi,title,year,license,abstract,pdf_url,full_text_url FROM articles WHERE doi=?",
            (doi,),
        ).fetchone()
        if not row:
            continue
        url = row["pdf_url"] or row["full_text_url"]
        if not url:
            continue
        target = CACHE / (_safe_name(doi) + ".pdf")
        try:
            if not target.is_file():
                target.write_bytes(_get(url))
            doc = fitz.open(target)
            text = "\n".join(page.get_text() for page in doc)
            images = sum(len(page.get_images(full=True)) for page in doc)
            refs = len(re.findall(r"(?m)^\s*\[?\d{1,3}\]?\s+[A-Z]", text))
            paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
            sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
            heading_hits = {
                key: len(re.findall(p, text, re.I))
                for key, p in {
                    "introduction": r"\bintroduction\b",
                    "conclusion": r"\bconclusions?\b",
                    "outlook": r"\boutlook\b",
                    "methods": r"\bmethods\b",
                    "references": r"\breferences\b",
                    "figure": r"\bfig(?:ure)?\.?\s*\d",
                    "table": r"\btable\s*\d",
                }.items()
            }
            rows.append({
                "doi": doi,
                "title": row["title"],
                "year": row["year"],
                "license": row["license"],
                "pdf_url": url,
                "pages": doc.page_count,
                "chars": len(text),
                "words": len(re.findall(r"\S+", text)),
                "images": images,
                "paragraphs": len(paragraphs),
                "sentences": len(sentences),
                "avg_sentence_words": round(
                    sum(len(re.findall(r"\S+", s)) for s in sentences) / max(1, len(sentences)), 1
                ),
                "references_est": refs,
                "abstract_chars": len(row["abstract"] or ""),
                **heading_hits,
            })
            doc.close()
        except Exception as exc:
            rows.append({"doi": doi, "error": str(exc), "url": url})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(rows, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
