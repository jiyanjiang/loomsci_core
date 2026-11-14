# LoomSci Core v0.1 · Platform Guide

- Status: **App Platform Preview**, not a stable public SDK
- Version: `0.1.0`
- API: `core/1`
- App API: `app/1`
- Python: 3.12
- Platforms: macOS + Windows (primary test targets)

## 1. What Core is

LoomSci Core is a small, local-first runtime for AI-native applications.

```text
Core = workspace + items + blobs + tags + search + app host + backup + updater
App  = domain model + UI + workflows + content
```

Core does not require an account. It binds to `127.0.0.1`, stores data under a
local workspace, and gives apps a stable HTTP/SDK surface.

Core is **not**:

- a chat UI
- a multi-user server
- a task/agent orchestrator
- a cloud sync service
- a report, project, or writing product

Those belong to apps.

## 2. Install and run

From the repository:

```bash
python3.12 -m venv .venv
./.venv/bin/pip install -r requirements-core.txt  # or install dependencies
./.venv/bin/python -m loomsci_core --home /tmp/loomsci-core --port 8795 start
./.venv/bin/python -m loomsci_core --home /tmp/loomsci-core status
./.venv/bin/python -m loomsci_core --home /tmp/loomsci-core stop
```

The `loomsci-v0` console script is also defined in `pyproject.toml`.

## 3. Workspace

```text
<home>/
├─ data/
│  ├─ core.db
│  └─ blobs/
├─ apps/<slug>/
│  ├─ manifest.json
│  ├─ code/
│  ├─ venv/
│  └─ data/
├─ backups/
├─ logs/
├─ runtime/core.json
└─ local.token
```

`local.token` is mode `0600`. Do not commit it.

## 4. Local security

```text
Authorization: Bearer <local.token>
```

- `/v1/health` and `/v1/version` are public.
- Every other endpoint requires the master token or a scoped app token.
- App tokens can only access their own `app` namespace.
- v0 has no cross-app read permission.
- No user account or cloud identity is required.

## 5. Concepts

### Item

A generic, readable record:

```json
{
  "id": "i-...",
  "app": "report",
  "type": "report.note",
  "title": "PISA",
  "body": "Markdown body",
  "metadata": {},
  "tags": [{"tag": "pisa", "source": "ai", "confidence": null}]
}
```

`type` is app-defined, conventionally `<app>.<type>`.

### Blob

A binary attachment linked to an item. Blobs live under `data/blobs/`.

### App

A separately versioned process managed by Core. Apps use `app/1` manifests and
are started with a scoped token.

### Backup

Data-only backup of core DB, blobs, app data, and installed app metadata.
Software/code/venv/token are excluded.

## 6. API and SDK

API reference: [core-api](core-api.md)  
OpenAPI: [openapi.json](../../openapi/core-v0.json)  
SDK: `loomsci_core.sdk.CoreClient`

```python
from loomsci_core.sdk import CoreClient

client = CoreClient("http://127.0.0.1:8795", token)
item = client.create_item(app="my-app", type="my-app.note", title="Hello", body="World")
print(client.search("Hello"))
```

## 7. App development

Read [app-developer](app-developer.md).  
Core maintainer guide: [core-maintainer](core-maintainer.md).

The first reference app is `examples/hello-app`.

## 8. Current limitations

This is a **preview**:

- no production installer yet
- no OpenAPI-generated client yet
- no third-party app marketplace
- no multi-user/auth
- no cross-app reads
- app CLI helpers are not complete
- signing and updater are prototypes
- no cloud sync

Do not promise production stability to end users.

## 9. Version policy

```text
core/1   additive changes only within v0.x
app/1    app manifest contract
```

Breaking changes require a new major (`core/2`) and a migration plan.
