# research v0.1

Deterministic research workspace, no LLM calls.

- prompt → `r-<hash>/vN` workspace;
- sources with URL/title/excerpt/grade;
- facts must reference an existing source;
- `fact_gate` requires 2 domains, a strong source, 2 citations, topical match;
- publish only when the gate passes;
- data lives in `packs/research/data/`.

Run:

```bash
python -m addons.research.server --home ~/.loomsci --port 8796
```

Open `http://127.0.0.1:8796/`.
