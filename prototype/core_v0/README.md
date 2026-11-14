# Core v0 prototype

Not product code. The first M1 slice: items, tags, blobs, FTS, and a local-token
API.

```bash
python3 prototype/core_v0/cli.py --home /tmp/loomsci-core-v0 --port 8795 start
python3 prototype/core_v0/cli.py --home /tmp/loomsci-core-v0 status
python3 prototype/core_v0/cli.py --home /tmp/loomsci-core-v0 stop
python3 prototype/test_core_v0.py
```

Implemented:

- SQLite schema: `items`, `item_tags`, `blobs`, `apps`, `items_fts`
- `GET /v1/health`, `/v1/version`, `/v1/status`
- item create/list/get/update/delete
- tags set/list
- FTS search
- blob upload/download/inline
- `Authorization: Bearer <local.token>`

Tested:

```text
macOS:   PASS
Windows: PASS
```

CLI lifecycle:

```text
start / duplicate-start / status / stop / stale state
migrated workspace start: PASS
```

M1 end-to-end:

```bash
MIGRATED_HOME=/path/to/migrated-home python3 prototype/test_core_m1.py
```

macOS PASS, Windows PASS. See `reports/core_m1/2026-11-14-m1-acceptance.md`.

App Host:

- install / start / stop / update / remove
- per-app venv
- scoped app token
- app can read/write only its own namespace
- app update/remove preserves data
- demo app writes an item through the Core API

Backup/restore:

- data-only backup of core DB, blobs, app data
- excludes token/logs/venv/code
- manifest sha256/bytes
- restore to a new workspace
- token regenerated

Not integrated yet:

- migration import
- the production CLI/updater
- full app package signature layout
