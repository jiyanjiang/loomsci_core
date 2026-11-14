# Report style registry

Styles are versioned internal profiles. They are not prompts copied from
publishers; they are extracted design rules with sample provenance and limits.

## Naming

```text
<family>-<variant>-v<major>.<minor>.<patch>
```

Examples:

```text
techreport-simple-v0.1.0
techreport-longform-v0.1.0
policy-brief-v0.1.0
technical-review-v0.1.0
```

Rules:

- `family` = deliverable class
- `variant` = audience/structure variant
- version bumps when acceptance rules or structure change
- style code must appear in every generated report manifest
- a style never changes silently; bump it

## Registry

| Code | Source | Status | Best for | Length |
|---|---|---|---|---|
| `techreport-simple-v0.1.0` | Nature Physics Perspective, 10 samples | draft | technical research brief, Perspective-style | 5k–12k words |
| `techreport-longform-v0.1.0` | not extracted | planned | 30–95 page manual, chapters | 30k+ words |
| `policy-brief-v0.1.0` | not extracted | planned | decision makers, policy audience | 2k–5k words |
| `technical-review-v0.1.0` | not extracted | planned | exhaustive method/field review | 15k–30k words |

## Extraction procedure

```text
1. select 10–20 real, licensed samples
2. store metadata + local PDFs (not redistributed)
3. extract structure, length, voice, figures, citations
4. write a style analysis
5. codify a JSON profile
6. apply it to one golden outline
7. human review
8. freeze the code version
```

## Application procedure

```text
question
→ choose style code
→ generate outline
→ check acceptance rules
→ generate report
→ attach style code + sample provenance to manifest
```

No style may be applied without:

- style code
- source sample set
- acceptance checklist
- reported limitations

## Current limitation

`techreport-simple-v0.1.0` is extracted from one genre only. It is a starting
point, not the definition of a good report. Other styles should be extracted
separately and compared on the same golden task.
