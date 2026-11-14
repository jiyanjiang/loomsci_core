# Report App · product spec v0

- Status: draft, 2026-11-14
- Product line: LoomSci Core + LoomSci Report
- Free app: public sources only
- Final deliverables: Markdown + PDF + EPUB
- References: `research.ask` flow, LoomReport, TAA p-64b4f07f, p-1a4bff83

## 1. Positioning

Report is the first free LoomSci app. It turns a research question into a
reproducible, source-grounded research brief and exports it as MD, PDF, and EPUB.

```text
question
→ query planning
→ public-source search
→ source registry
→ evidence extraction
→ synthesis
→ deterministic verification
→ MD / PDF / EPUB
```

Not a chat UI, not a generic search engine, not a paid-database reader.

## 2. Free-source boundary

Free Report uses only public and open resources:

- PubMed / PMC
- arXiv (local database allowed)
- Nature Physics open-access articles
- DeepSeek Search API / web search / deep-thinking search / file input / link reading
- Crossref / OpenAlex / Unpaywall metadata when needed

Rules:

- Do not scrape paywalled full text.
- Store metadata, abstract, OA full text, and source URL.
- Store content hash and access date.
- A source that cannot be verified is not eligible for citation.
- Paid lexicon/PMC full-database access is a later paid app, not free Report.

## 3. Golden tasks

### G1 · PISA science communication

Source: TAA `p-64b4f07f`.

This is a real demand: a multi-part, figure-rich research report on PISA and
science communication. It is the first end-to-end acceptance task.

### G2 · 95-page manual

Source: TAA `p-1a4bff83`.

This is the quality/format reference: long-form PDF, chapters, references,
tables, figures, page checks. Report does not need 95 pages by default, but the
export pipeline must support that scale.

## 4. Source model

```text
articles
  id
  doi
  pmid
  pmcid
  arxiv_id
  title
  abstract
  authors_json
  journal
  year
  article_type
  oa_status
  license
  url
  full_text_url
  source
  fetched_at
  content_hash

article_matches
  left_id
  right_id
  method
  confidence

report_sources
  report_id
  article_id
  role
  claim_ids_json
```

Priority:

```text
PMC / arXiv full text
→ Nature Physics open access
→ PubMed abstract
→ metadata-only fallback
```

## 5. Ingestion plan

1. Collect Nature Physics `perspective` articles.
2. Resolve DOI, year, authors, license, OA status.
3. Match each article against PMC and the local arXiv database.
4. Store only metadata/abstract/OA full text; never copy paywalled text.
5. Build a seed library of 50–100 matched articles.
6. Use the seed library for retrieval and export tests before live web use.

The seed library is a test fixture, not a redistributed corpus.

## 6. Report pipeline

```text
1. intake
   question, audience, language, length, figures, deadline

2. query plan
   3–6 queries; background terms + main terms; English/Chinese where useful

3. search
   DeepSeek Search + PMC + arXiv + Nature OA; dedupe by DOI/PMID/arXiv

4. source registry
   title, authors, year, venue, URL, license, access date, hash

5. evidence
   claim, excerpt, source, evidence level, section

6. synthesis
   only registered sources; cite every factual claim

7. verification
   URL/ID resolves; excerpt matches; citation coverage; contradiction flagged

8. render
   canonical MD → PDF + EPUB
```

## 7. Evidence levels

```text
L0  model inference, no source
L1  topic-related source only
L2  abstract supports the claim
L3  full text supports the claim
L4  full text + figure/table supports the claim
L5  multiple independent sources support the claim
```

Report should display the level for key claims. A claim below L2 cannot be
presented as established fact.

## 8. Deliverables

### Markdown

- canonical source of truth
- YAML front matter
- `[F###]` citations
- figure/table references
- source appendix

### PDF

- cover, TOC, chapters, figures, tables, references
- page numbers and running headers
- no clipped tables, no blank near-empty pages
- page count and layout checks

### EPUB

- reflowable
- navigation/TOC
- images with alt text
- footnotes/endnotes
- `epubcheck` clean

### Repro manifest

```json
{
  "report_id": "...",
  "question": "...",
  "sources": ["..."],
  "prompt_version": "...",
  "model": "...",
  "created_at": "...",
  "outputs": {"md": "...", "pdf": "...", "epub": "..."}
}
```

## 9. Quality gates

- 100% of citation URLs/IDs resolve or are explicitly marked unavailable.
- 100% of citations map to a registered source.
- No uncited factual claims in the final report.
- At least 3 sources from 2 independent domains for a research brief.
- 20 sampled claims: human support rate ≥ 95%.
- No fabricated DOI/PMID/arXiv ID.
- PDF: no overflow, no missing figures, TOC page numbers match.
- EPUB: `epubcheck` passes.
- Same source set and prompt version produce a reproducible report.

## 10. App boundary

Report owns:

```text
reports, sources, evidence, render jobs, templates, daily content
```

Report uses Core:

```text
items, blobs, tags, search, app host, backup
```

Report does not:

- execute agents
- manage projects
- run a paid database
- handle accounts/billing
- scrape paywalled text

## 11. Stages

| Stage | Goal | Acceptance |
|---|---|---|
| R0 | source schema + 50–100 seed articles | metadata/OA status/matches verified |
| R1 | ingestion + query/search | 3 queries produce deduped, resolvable sources |
| R2 | synthesis + evidence levels | citations resolve; no uncited claims |
| R3 | MD → PDF + EPUB | PDF layout checks; `epubcheck` clean |
| R4 | golden tasks | PISA report + 95-page-scale manual pass |
| R5 | free beta | 5 technical users; export and source audit pass |

## 12. Non-goals for v0

- paid full-text database
- automatic PDF of every paywalled article
- multi-user collaboration
- real-time news feed
- arbitrary web scraping
- model-generated citations
