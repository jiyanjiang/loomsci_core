# Report seed library · Nature Physics perspectives

- Date: 2026-11-14
- Local database: `data/report/report_seed.db` (gitignored)
- Build: `python scripts/build_report_seed.py`
- Check: `python scripts/check_report_seed.py`

## Acceptance

| Metric | Target | Actual |
|---|---:|---:|
| Real Nature Physics perspectives | ≥10 | 50 |
| Open access | ≥10 | 26 |
| CC license | ≥10 | 13 |
| OA full-text/PDF URL | ≥10 | 26 |
| Matched PMC/arXiv | ≥5 | 9 |
| Unique DOI | 100% | 50/50 |
| Missing DOI/title | 0 | 0 |

**Result: PASS.**

## Sources

- Nature Physics `perspective` listing: https://www.nature.com/nphys/articles?type=perspective
- OpenAlex for metadata and OA status
- Europe PMC DOI lookup
- local arXiv DuckDB exact-title matching

## Open-access sample

| Year | Title | DOI | License | PMC | arXiv |
|---:|---|---|---|---|---|
| 2026 | An integrated theoretical and numerical approach to understand modern experiments on quantum magnetism | 10.1038/s41567-026-03304-5 | cc-by | — | — |
| 2026 | Loop-current order in kagome metals | 10.1038/s41567-026-03229-z | — | — | — |
| 2025 | Challenges and opportunities in orbitronics | 10.1038/s41567-025-03143-w | cc-by | — | 2509.23954 |
| 2025 | Chiral phonons | 10.1038/s41567-025-03001-9 | other-oa | — | — |
| 2025 | Topology shapes dynamics of higher-order networks | 10.1038/s41567-024-02757-w | other-oa | — | — |
| 2024 | Drug design on quantum computers | 10.1038/s41567-024-02411-5 | — | — | 2301.04114 |
| 2024 | Opportunities in nanoscale probing of laser-driven phase transitions | 10.1038/s41567-024-02603-z | cc-by | — | — |
| 2023 | In search of Majorana | 10.1038/s41567-022-01900-9 | public-domain | — | 2210.17365 |
| 2022 | Citation inequity and gendered citation practices in contemporary physics | 10.1038/s41567-022-01770-1 | cc-by | — | — |
| 2022 | Disruption prediction with artificial intelligence techniques in tokamak plasmas | 10.1038/s41567-022-01602-2 | cc-by | — | — |
| 2022 | From atomically resolved imaging to generative and causal models | 10.1038/s41567-022-01666-0 | cc-by | — | — |
| 2021 | Charge order and superconductivity in kagome materials | 10.1038/s41567-021-01404-y | other-oa | — | — |
| 2021 | The physics of higher-order interactions in complex systems | 10.1038/s41567-021-01371-4 | — | — | 2110.06023 |
| 2020 | From precision physics to the energy frontier with the Compact Linear Collider | 10.1038/s41567-020-0834-8 | cc-by | — | — |
| 2020 | Future Circular Colliders succeeding the LHC | 10.1038/s41567-020-0856-2 | cc-by | — | — |
| 2020 | Particle physics at accelerators in the United States and Asia | 10.1038/s41567-020-0863-3 | — | — | 2006.10583 |
| 2020 | Tail risk of contagious diseases | 10.1038/s41567-020-0921-x | — | — | 2004.08658 |
| 2020 | The quest for new physics with the Physics Beyond Colliders programme | 10.1038/s41567-020-0838-4 | cc-by | — | — |
| 2020 | Topology and broken Hermiticity | 10.1038/s41567-020-01093-z | cc-by-nc-nd | — | — |
| 2019 | From networks to optimal higher-order models of complex systems | 10.1038/s41567-019-0459-y | other-oa | https://www.ncbi.nlm.nih.gov/pmc/articles/6445364 | — |

Full open-access records: 26. See CSV for all 50 records.

## Notes

- The DB and JSON cache stay local and are not committed; this report and the CSV manifest are the reviewable artifacts.
- Full text is not redistributed. Only metadata, abstract, OA URL, hash, and match IDs are stored.
- Next: validate the 26 OA URLs, then use 5–10 articles to test the source registry → citation pipeline.
