# Bug log

This directory is the intake log for user-visible defects.

## Batch-fix rule

**Do not start a bug-fix batch until at least 10 bugs are open.**

```bash
python scripts/buglog.py status
python scripts/buglog.py gate
```

`gate` exits `0` when the open count reaches the threshold and `1` while it is
below it. The threshold is intentionally high: it keeps us from turning every
single report into an immediate context switch.

Exceptions are limited to defects explicitly classified as security or data
loss, and require the owner to say so in the report.

## One file per bug

Create a report with:

```bash
python scripts/buglog.py new \
  --title "Ordered lists collapse into a paragraph" \
  --surface "collab, notify" \
  --severity P2
```

Each report is `bugs/NNNN-short-slug.md` with YAML front matter:

```yaml
---
id: BUG-0001
title: Ordered lists collapse into a paragraph
status: open
severity: P2
surface: collab, notify
reported: 2026-11-11
---
```

Statuses:

- `open` — reproduced, waiting for the batch threshold
- `in-progress` — assigned to an active batch
- `fixed` — fix merged and verified
- `closed` — not reproducible, duplicate, or by design
- `blocked` — waiting on external information

Severity:

- `P0` — data loss, security, or complete loss of a core workflow
- `P1` — core workflow broken with no workaround
- `P2` — incorrect rendering or degraded workflow with a workaround
- `P3` — cosmetic

## Report contents

Every report must contain:

1. exact reproduction text or steps
2. expected output
3. actual output
4. surface and renderer/file
5. evidence (screenshot, DOM, command output)
6. root-cause note, if known
7. explicit fix scope, without implementing it before the gate opens

Do not close a report by changing test wording or by suppressing the symptom.
