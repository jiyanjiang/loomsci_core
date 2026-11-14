# Core v0 Maintainer Guide

- Audience: maintainers of `loomsci_core`
- Status: minimal `0.1.0`; API `core/1`
- Tests: `python -m unittest discover -s tests -q`

## 1. Repository layout

```text
loomsci_core/
├─ store.py       SQLite items/tags/blobs/apps/FTS
├─ server.py      Flask API and auth
├─ app_host.py    app install/start/stop and scoped tokens
├─ backup.py      data-only backup/restore
├─ cli.py         start/stop/status
├─ sdk.py         public SDK
├─ version.py     version/API constants
└─ __main__.py    python -m loomsci_core

examples/hello-app/  SDK reference app
tests/               Core and SDK tests
docs/                minimal platform, API, app, maintainer guides
```

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

## 3. API rules

`core/1` is additive.

Allowed:

- new optional fields
- new endpoints
- new response fields

Not allowed without `core/2`:

- removing or renaming fields
- changing item/blob identity
- changing backup format
- changing app lifecycle
- changing token semantics

App-specific requirements stay in the app.

## 4. App isolation

- Scoped tokens map token to app slug.
- App tokens cannot read another app.
- No cross-app reads in v0.
- App code and venv are not in data backups.
- App data lives under `apps/<slug>/data/`.

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
Restore requires an empty target; the token is regenerated.

## 6. Tests

```bash
python -m unittest discover -s tests -q
python -m unittest tests.test_loomsci_core -v
python -m unittest tests.test_loomsci_core_sdk -v
```

Target platforms: macOS and Windows.

## 7. Release checklist

- [ ] tests green
- [ ] API docs and OpenAPI updated
- [ ] example app runs
- [ ] backup/restore tested
- [ ] macOS start/stop
- [ ] Windows start/stop
- [ ] no private paths, tokens, or keys in the public tree
- [ ] `VERSION`, `pyproject.toml`, and `loomsci_core.version` agree
- [ ] tag and release notes

## 8. Security

- bind loopback only
- local token mode `0600`
- scoped app token
- no cross-app reads
- no secrets in logs
- no app-to-app RPC

## 9. Out of scope

Not part of this version:

- installer, updater, signed packages
- app update/remove commands
- migration tools
- app marketplace
- external accounts or multi-user
- cloud sync
- conformance suite for third-party apps
