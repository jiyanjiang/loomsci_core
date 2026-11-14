#!/usr/bin/env python3
"""Build a small, reproducible Report seed library.

Sources:
- Nature Physics `perspective` listing
- OpenAlex metadata / OA status
- Europe PMC DOI lookup
- local arXiv DuckDB (best-effort exact-title match)

This is a sample library, not a redistributed corpus.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "report"
CACHE = DATA / "nature_physics_perspectives.json"
DB = DATA / "report_seed.db"
ARXIV_DB = Path(os.environ.get("LOOMSCI_ARXIV_DB", ""))
USER_AGENT = "loomsci-report-seed/0.1 (+local research)"


def _get(url: str, timeout: int = 30) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def _json(url: str) -> dict[str, Any]:
    return json.loads(_get(url).decode("utf-8"))


def _nature_links() -> list[tuple[str, str]]:
    found: dict[str, str] = {}
    for page in range(1, 10):
        url = f"https://www.nature.com/nphys/articles?type=perspective&page={page}"
        try:
            html = _get(url).decode("utf-8", "replace")
        except Exception:
            continue
        batch = 0
        pattern = re.compile(
            r'<h3[^>]*class="c-card__title"[^>]*>\s*<a\s+href="(/articles/s41567-[^"]+)"[^>]*>(.*?)</a>',
            re.S,
        )
        for match in pattern.finditer(html):
            href = match.group(1)
            title = re.sub(r"<[^>]+>", "", match.group(2)).strip()
            if href not in found:
                found[href] = title
                batch += 1
        if not batch:
            break
    return list(found.items())


def _abstract(index: dict[str, list[int]] | None) -> str:
    if not index:
        return ""
    words: list[tuple[int, str]] = []
    for word, positions in index.items():
        for pos in positions:
            words.append((int(pos), word))
    return " ".join(word for _, word in sorted(words))


def _collect() -> list[dict[str, Any]]:
    if CACHE.is_file():
        return json.loads(CACHE.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    for href, fallback_title in _nature_links():
        doi = "10.1038/" + href.split("/articles/")[1]
        try:
            work = _json(
                "https://api.openalex.org/works/https://doi.org/"
                + urllib.parse.quote(doi, safe="")
            )
        except Exception as exc:
            rows.append({"doi": doi, "title": fallback_title, "error": str(exc)})
            continue
        oa = work.get("open_access") or {}
        best = work.get("best_oa_location") or {}
        location = work.get("primary_location") or {}
        rows.append({
            "doi": doi,
            "title": work.get("title") or fallback_title,
            "abstract": _abstract(work.get("abstract_inverted_index")),
            "authors": [
                (item.get("author") or {}).get("display_name")
                for item in work.get("authorships") or []
                if (item.get("author") or {}).get("display_name")
            ],
            "journal": (location.get("source") or {}).get("display_name") or "Nature Physics",
            "year": work.get("publication_year"),
            "publication_date": work.get("publication_date"),
            "article_type": "perspective",
            "is_oa": bool(oa.get("is_oa")),
            "oa_url": oa.get("oa_url"),
            "license": best.get("license"),
            "pdf_url": best.get("pdf_url"),
            "url": work.get("doi") or location.get("landing_page_url"),
            "pmid": (work.get("ids") or {}).get("pmid"),
            "pmcid": (work.get("ids") or {}).get("pmcid"),
            "openalex_id": work.get("id"),
        })
        time.sleep(0.1)
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return rows


def _europe_pmc(doi: str) -> dict[str, Any]:
    query = urllib.parse.quote(f'DOI:"{doi}"')
    try:
        data = _json(
            "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
            f"?query={query}&format=json&resultType=lite&pageSize=1"
        )
    except Exception:
        return {}
    results = ((data.get("resultList") or {}).get("result") or [])
    return results[0] if results else {}


def _arxiv_titles(titles: list[str]) -> dict[str, str]:
    if not titles or not ARXIV_DB.is_file():
        return {}
    try:
        import duckdb
    except Exception:
        return {}
    values = [str(title).lower() for title in titles if title]
    if not values:
        return {}
    placeholders = ",".join("?" for _ in values)
    try:
        conn = duckdb.connect(str(ARXIV_DB), read_only=True)
        rows = conn.execute(
            f"SELECT lower(title), arxiv_id FROM papers WHERE lower(title) IN ({placeholders})",
            values,
        ).fetchall()
        conn.close()
        return {str(title): str(arxiv_id) for title, arxiv_id in rows if arxiv_id}
    except Exception:
        return {}

def _schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS articles (
      id TEXT PRIMARY KEY,
      doi TEXT UNIQUE,
      source TEXT NOT NULL,
      title TEXT NOT NULL,
      abstract TEXT,
      authors_json TEXT NOT NULL DEFAULT '[]',
      journal TEXT,
      year INTEGER,
      publication_date TEXT,
      article_type TEXT,
      oa_status INTEGER NOT NULL DEFAULT 0,
      license TEXT,
      url TEXT,
      full_text_url TEXT,
      pdf_url TEXT,
      pmid TEXT,
      pmcid TEXT,
      arxiv_id TEXT,
      openalex_id TEXT,
      fetched_at TEXT NOT NULL,
      content_hash TEXT
    );
    CREATE TABLE IF NOT EXISTS article_matches (
      left_id TEXT NOT NULL,
      right_id TEXT NOT NULL,
      method TEXT NOT NULL,
      confidence REAL,
      note TEXT,
      PRIMARY KEY (left_id, right_id, method)
    );
    CREATE TABLE IF NOT EXISTS seed_runs (
      id TEXT PRIMARY KEY,
      created_at TEXT NOT NULL,
      total INTEGER NOT NULL,
      oa INTEGER NOT NULL,
      matched INTEGER NOT NULL
    );
    """)


def build(rows: list[dict[str, Any]]) -> dict[str, Any]:
    DATA.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB)
    try:
        _schema(conn)
        conn.execute("DELETE FROM article_matches")
        conn.execute("DELETE FROM articles")
        conn.execute("DELETE FROM seed_runs")
        stamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        oa = 0
        matched = 0
        arxiv_map = _arxiv_titles([str(row.get("title") or "") for row in rows])
        for row in rows:
            doi = str(row.get("doi") or "")
            if not doi:
                continue
            article_id = "natphys:" + doi
            title = str(row.get("title") or "")
            digest = hashlib.sha256(
                json.dumps(row, ensure_ascii=False, sort_keys=True).encode("utf-8")
            ).hexdigest()
            is_oa = 1 if row.get("is_oa") else 0
            oa += is_oa
            pmc = _europe_pmc(doi)
            pmcid = row.get("pmcid") or pmc.get("pmcid") or ""
            pmid = row.get("pmid") or pmc.get("pmid") or ""
            arxiv_id = arxiv_map.get(title.lower())
            conn.execute(
                "INSERT OR REPLACE INTO articles("
                "id,doi,source,title,abstract,authors_json,journal,year,publication_date,"
                "article_type,oa_status,license,url,full_text_url,pdf_url,pmid,pmcid,"
                "arxiv_id,openalex_id,fetched_at,content_hash) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    article_id, doi, "nature_physics", title, row.get("abstract") or "",
                    json.dumps(row.get("authors") or [], ensure_ascii=False),
                    row.get("journal") or "Nature Physics", row.get("year"),
                    row.get("publication_date") or "", "perspective", is_oa,
                    row.get("license") or "", row.get("url") or "",
                    row.get("oa_url") or "", row.get("pdf_url") or "",
                    pmid, pmcid, arxiv_id or "", row.get("openalex_id") or "",
                    stamp, digest,
                ),
            )
            if pmcid:
                conn.execute(
                    "INSERT OR REPLACE INTO article_matches(left_id,right_id,method,confidence,note) "
                    "VALUES(?,?,?,?,?)",
                    (article_id, pmcid, "europe_pmc_doi", 1.0, "DOI lookup"),
                )
                matched += 1
            if arxiv_id:
                conn.execute(
                    "INSERT OR REPLACE INTO article_matches(left_id,right_id,method,confidence,note) "
                    "VALUES(?,?,?,?,?)",
                    (article_id, arxiv_id, "arxiv_exact_title", 1.0, "exact title"),
                )
                matched += 1
        run_id = "seed-" + stamp
        conn.execute(
            "INSERT INTO seed_runs(id,created_at,total,oa,matched) VALUES(?,?,?,?,?)",
            (run_id, stamp, len(rows), oa, matched),
        )
        conn.commit()
        return {"run_id": run_id, "total": len(rows), "oa": oa, "matched": matched, "db": str(DB)}
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rebuild-cache", action="store_true")
    args = parser.parse_args()
    if args.rebuild_cache:
        CACHE.unlink(missing_ok=True)
    rows = _collect()
    result = build(rows)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
