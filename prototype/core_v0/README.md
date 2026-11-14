# Core v0 prototype

Not product code. The first M1 slice: items, tags, blobs, FTS, and a local-token
API.

```bash
python3 prototype/core_v0/server.py --home /tmp/loomsci-core-v0 --port 8795
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

Not integrated yet:

- App Host (install/start/stop/update/remove)
- backup/restore
- scoped per-app tokens
- app registry validation
- migration import
- the production CLI/updater
