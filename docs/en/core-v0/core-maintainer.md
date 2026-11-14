# Core v0 Maintainer Guide

- Audience: maintainers of `loomsci_core`
- Status: preview; `core/1`
- Tests: `python -m unittest discover -s tests -q`

## 1. Repository layout

```text
loomsci_core/          formal Core package
├─ store.py            SQLite items/tags/blobs/apps/FTS
├─ server.py           Flask API and auth
├─ app_host.py         app processes and scoped tokens
├─ backup.py           data-only backup/restore
├─ cli.py              start/stop/status/doctor
├─ sdk.py              public SDK
├─ version.py          version/API constants
└─ __main__.py         python -m loomsci_core

examples/hello-app/    SDK reference app
prototype/             non-product research/prototypes
tests/                 existing product + formal package tests
docs/                  contracts and guides
```

`prototype/` is **not** the product. Do not ship it or point app developers at it.

## 2. Data

```text
<home>/data/core.db
<home>/data/blobs/
<home>/apps/<slug>/data/
<home>/local.token
```

- items/tags/blobs/apps/items_fts are Core.
- App data belongs to the app.
- Never put app-specific tables into Core.
- FTS is derived; rebuild from items.

## 3. API changes

`core/1` is additive.

Allowed:

- new optional fields
- new endpoints
- new response fields

Not allowed without `core/2`:

- removing/renaming fields
- changing item/blob identity
- changing backup format
- changing app lifecycle
- changing token semantics

If a requirement is app-specific, push it to the app.

## 4. App isolation

- Scoped tokens map token -> app slug.
- App tokens cannot read another app.
- No `items.cross_read` in v0.
- App code/venv are not in data backups.
- App update/remove preserves `apps/<slug>/data/`.

## 5. Backup

Data-only:

```text
data/core.db
data/blobs/
apps/<slug>/data/
apps/installed.json
manifest.json
```

Excluded: token, logs, venv, code, cache.

Restore requires an empty target; token is regenerated.

## 6. Updater

Prototype chain:

```text
verify signed package
→ backup
→ stop Core
→ atomic payload replace
→ start
→ health
→ rollback on failure
```

Current prototype uses a marker payload; full package replacement remains.

## 7. Tests

```bash
python -m unittest discover -s tests -q
python -m unittest tests.test_loomsci_core -v
python -m unittest tests.test_loomsci_core_sdk -v
python prototype/test_core_m1.py
```

Platform matrix: macOS + Windows. Linux is deferred.

## 8. Release checklist (pre-C1)

- [ ] tests green
- [ ] API docs/OpenAPI updated
- [ ] manifest/SDK examples updated
- [ ] backup/restore tested
- [ ] migration dry-run/apply tested
- [ ] signed updater tested
- [ ] macOS install/start
- [ ] Windows install/start
- [ ] no private paths/keys in public tree
- [ ] version and changelog updated
- [ ] rollback tag

## 9. Security

- bind loopback only
- local token 0600
- app token scoped
- no cross-app reads
- package signatures before extraction
- no secrets in logs
- no arbitrary app-to-app RPC

## 10. Migration

beta.28 -> v0 plan:

- source read-only
- new workspace
- posts -> items
- attachments -> blobs
- facts -> project.fact items
- projects/tasks -> Project DB
- summaries/mentions/reads -> legacy archive
- verify counts/hashes before switch

## 11. Known gaps

- full package updater
- clean installers
- OpenAPI-generated SDK
- conformance suite
- app CLI commands
- external demo apps
- 30-day no-breaking window
- C1 review
