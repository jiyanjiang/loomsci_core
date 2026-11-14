# Nature Physics Perspective style analysis · v0

- Date: 2026-11-14
- Sample: 10 open-access Nature Physics `perspective` records from the seed library
- Purpose: derive a first style profile for LoomSci Report
- Caveat: this is **one style family**, not a universal definition of a good report
- Copyright: only aggregate observations; no full text is reproduced

## 1. Sample

Selected 10 records (2018–2026), including Nature-hosted PDFs and arXiv author
manuscripts. The seed DB contains 26 open-access records; style analysis used 10
PDFs, while metadata covers all 50.

Some Nature PDFs include an HTML wrapper or only a subset of pages. Quantitative
ranges below exclude obvious extraction artifacts (for example, a 70-page HTML
wrapper) and should be treated as approximate.

## 2. Quantitative range

Across usable PDFs:

| Metric | Observed range | Interpretation |
|---|---:|---|
| Pages | 6–20 | Perspective, not a 100-page review |
| Words | ~5,500–12,800 | dense but readable |
| Average sentence length | ~10–18 words | short, declarative |
| Figures | 3–36 images (layout-dependent) | figures carry argument, not decoration |
| References | roughly 50–100 | primary literature, not exhaustive catalogue |
| Abstract | short, ~120–200 words | context → gap → proposal |

The 95-page manual is a different product (long-form deliverable), not the
Perspective style baseline.

## 3. Structural pattern

The strongest recurring pattern is:

```text
Field context
→ unresolved tension / gap
→ why this matters now
→ current state of evidence
→ challenges / competing approaches
→ opportunities
→ proposed agenda / outlook
→ conclusion
```

Not every article uses the same headings, but the argument sequence is stable.

Common section roles:

1. **Opening**: field status in 2–4 paragraphs; no generic “in this article”.
2. **State of the field**: what is established, what is contested.
3. **Tension**: why the current approach is insufficient.
4. **Opportunity**: what becomes possible, often with a concrete agenda.
5. **Outlook**: risks, open questions, what to do next.
6. **References**: primary sources; no bibliography dump.

## 4. Voice

Observed style:

- first-person plural: “we argue”, “we propose”, “we highlight”
- assertive but bounded: claims are qualified by evidence scope
- forward-looking: the perspective is a position, not only a summary
- short paragraphs, one argument per paragraph
- definitions early; jargon is introduced before use
- no marketing adjectives, no “revolutionary”, no “unprecedented” unless sourced

The voice is **argumentative and evidence-anchored**, not encyclopedic.

## 5. Title and abstract

Titles are usually:

- 8–15 words
- field + object + claim/tension
- sometimes a short question or a deliberate contrast

Examples of title shapes:

```text
<Field> and <challenge>
<Approach> for <goal>
The quest for <X> with <Y>
<Theme>: challenges and opportunities
```

Abstracts do four things quickly:

```text
1. establish the field
2. state the unresolved problem
3. summarize the evidence/approach
4. propose the perspective/agenda
```

## 6. Figures and tables

- Figures are conceptual or synthetic, not only data plots.
- A figure usually carries one argument: mechanism, taxonomy, roadmap, or
  comparison.
- Captions are self-contained and explain the claim, not only the axes.
- Tables are used for comparison/decision, not raw data dumps.

For Report, figures should be generated only when they carry an argument:
timeline, evidence map, comparison matrix, decision surface, research tree.

## 7. Citation behavior

- Citations support specific claims, not whole paragraphs.
- Primary literature dominates; reviews are used for orientation.
- References are concentrated around contested claims and technical methods.
- A Perspective does not try to cite everything; it cites what changes the
  argument.

Report rule:

```text
every factual claim → source
every source → registry entry
no registry entry → no citation
```

## 8. What not to copy

- Nature-specific front matter, journal metadata, and paywall layout.
- Dense undefined jargon.
- Citation padding.
- Author-manuscript formatting artifacts.
- The assumption that every report must be 6–20 pages; Report may need 30–95
  pages for a manual, but the **argument structure** should remain.

## 9. Report style profile v0

Use this as the first generation profile:

```text
Role: authoritative Perspective writer, not a chatbot
Audience: technical peers and informed researchers
Length: 5,000–12,000 words for a research brief; longer only for a manual
Structure: context → tension → evidence → challenges → opportunities → agenda
Voice: first-person plural; short declarative sentences; bounded claims
Citations: every factual claim; primary sources first
Figures: 3–8 conceptual figures for a brief; each must carry an argument
Forbidden: generic openings, marketing language, uncited numbers, fake citations
```

### Generation prompt skeleton

```text
Write a Perspective-style research report for [audience] on [question].
Open with the field context and the unresolved tension, not with “in this article”.
Use 4–7 sections. Each section must make one argument and cite registered sources.
Use first-person plural. Keep sentences short. Qualify uncertain claims.
Include 3–8 figures only when they carry an argument.
End with a concrete research agenda and open questions.
Do not invent citations, numbers, or sources.
```

## 10. Acceptance for style v0

A generated report passes style review if:

1. title is 8–20 words and names field + claim/tension;
2. abstract has context, gap, evidence, proposal;
3. 4–7 sections follow the argument sequence;
4. each section has a clear claim, not a topic label only;
5. no generic “in this article” opening;
6. no marketing adjectives without evidence;
7. every factual claim has a citation;
8. figures have self-contained captions and a reason to exist;
9. conclusion contains an agenda/open questions, not a summary only;
10. the report can be read without the appendix and still make sense.

## 11. Limits

- 10 samples are enough for a first style profile, not for a universal claim.
- Nature Physics Perspective is one genre; Report may need a clinical, technical,
  or policy variant later.
- Style is not a substitute for evidence quality. A well-written report with
  weak sources fails.

## 12. Next

1. Freeze `report-style-v0` as a prompt/profile.
2. Apply it to one golden task outline (PISA science communication).
3. Compare generated outline against the style acceptance list.
4. Only then start PDF/EPUB rendering.
