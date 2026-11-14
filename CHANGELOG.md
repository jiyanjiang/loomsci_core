# Changelog

## 0.2.0 — Core Web UI

- Added a built-in Core Web UI at `/` and `/app`.
- Create, list, edit, delete, tag, search, attach files, and create backups from
  the browser.
- Item responses now include their blobs.
- UI assets are served from `/assets/` without requiring a bearer token; API
  calls still require the local token.
- macOS browser acceptance passed: create, edit, delete, search, attachment,
  backup, and restart persistence.

## 0.1.1 — Windows quickstart

- Added Windows PowerShell install and run commands to README and platform docs.
- Added a PowerShell first-item example.
- No Core behavior change.

## 0.1.0 — minimal public beta

Minimal Core public beta. macOS and Windows release gates passed in CI run
`43579862388` at commit `90975fe`.

### Included

- local workspace
- items, tags, blobs, FTS search
- local master token and scoped app tokens
- items/search/blob API
- App Host install/start/stop
- data-only backup/restore
- CLI start/stop/status
- Python SDK
- `examples/hello-app`
- minimal platform/API/app/maintainer docs

### Excluded

- installer, updater, signed packages
- migration from the legacy beta product
- app update/remove commands
- app marketplace
- accounts, multi-user, cloud sync
- cross-app reads
