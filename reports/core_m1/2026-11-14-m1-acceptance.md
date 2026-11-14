# Core M1 acceptance · 2026-11-14

- Scope: Core v0 + App Host + backup/restore + migrated workspace
- Platforms: macOS A + Windows B
- Result: **PASS** for the M1 slice
- Not included: production package layout, updater, signed full installer

## 1. Test

`prototype/test_core_m1.py`

```text
start Core
→ create item
→ upload blob
→ install demo app
→ start demo app
→ app writes item through scoped token
→ stop app
→ create backup
→ stop Core
→ restore to new home
→ start restored Core
→ verify item / blob / app data / search
→ start migrated workspace
→ verify items
→ stop Core
```

## 2. Results

| Case | macOS | Windows |
|---|---|---|
| Core CLI start | PASS | PASS |
| item create | PASS | PASS |
| blob upload | PASS | PASS |
| demo app install/start | PASS | PASS |
| app writes through scoped token | PASS | PASS |
| backup | PASS | PASS |
| restore to new home | PASS | PASS |
| restored item/blob/app data | PASS | PASS |
| restored search | PASS | PASS |
| migrated workspace start | PASS | PASS |
| migrated items | 50 | 200 (limit) |
| CLI stop | PASS | PASS |

## 3. Caveats

- Demo app is a prototype, not a signed distributable app.
- Backup excludes app code/venv by design; restored apps need reinstall to start.
- The migration workspace is a local test copy, not a user-facing migration flow.
- Product updater is not implemented.
- Full app package signature layout is not integrated.

## 4. Decision

M1 slice is functionally connected end-to-end on both platforms.

Next:

1. Product updater/signed package integration.
2. M1 formal review.
3. Report app implementation only after M1 closes.

`beta.28` remains unchanged.
