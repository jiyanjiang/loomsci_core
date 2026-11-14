# Core v0 App Developer Guide

- Audience: developers building apps on `core/1`
- Status: preview; app API is `app/1`
- Reference app: `examples/hello-app`
- SDK: `loomsci_core.sdk.CoreClient`

## 1. What an app owns

```text
domain schema
UI
workflows
content
optional account/payment
```

It does not own:

```text
Core DB
Core token
App Host
backup/update
```

## 2. Minimal app layout

```text
my-app/
├─ manifest.json
└─ my_app/
   ├─ __init__.py
   └─ server.py
```

`manifest.json`:

```json
{
  "name": "My App",
  "slug": "my-app",
  "version": "0.1.0",
  "app_api": "app/1",
  "core_api": "core/1",
  "min_core": "0.1.0",
  "package": "my_app",
  "entry": "server",
  "port": 0,
  "health": "/health",
  "data_namespace": "app_my_app",
  "permissions": ["items.read", "items.write"],
  "update_channels": ["stable"],
  "content_channels": [],
  "preserve": ["data"],
  "uninstall": "keep_data",
  "requires_registration": false
}
```

## 3. Process contract

Core starts:

```text
<app-venv>/python -m <package>.<entry>
```

Environment:

```text
LOOMSCI_CORE_URL
LOOMSCI_APP_TOKEN
LOOMSCI_APP_SLUG
LOOMSCI_APP_PORT
LOOMSCI_APP_DATA_DIR
LOOMSCI_APP_LOG_DIR
```

The app must:

- bind `127.0.0.1:LOOMSCI_APP_PORT`
- serve `GET /health` with 200 + `{"ok":true}`
- exit when terminated
- not fork a daemon
- not log the token

## 4. SDK usage

```python
from loomsci_core.sdk import CoreClient

client = CoreClient(
    os.environ["LOOMSCI_CORE_URL"],
    os.environ["LOOMSCI_APP_TOKEN"],
)

item = client.create_item(
    app="my-app",
    type="my-app.note",
    title="Hello",
    body="Markdown",
    tags=["demo"],
)
print(client.search("Hello"))
```

SDK methods:

```text
health
create_item / get_item / list_items / update_item / delete_item
set_tags / list_tags
search
upload_blob / download_blob
```

Do not import `loomsci_core.store`, `app_host`, `server`, or `backup`.
They are Core internals.

## 5. Scoped access

An app token is limited to its own `app` namespace:

- create item: `app` must equal manifest slug
- list/get/update/delete: only own items
- search/tags: only own namespace
- backups/app management: forbidden

No cross-app read in v0.

## 6. Install and run

Current preview uses the API:

```bash
python -m loomsci_core --home /tmp/core --port 8795 start
TOKEN=$(cat /tmp/core/local.token)

curl -sS -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"source":"/absolute/path/to/my-app"}' \
  http://127.0.0.1:8795/v1/apps/install

curl -sS -H "Authorization: Bearer $TOKEN" \
  -X POST http://127.0.0.1:8795/v1/apps/my-app/start
```

CLI `loomsci app ...` helpers are not complete in this preview.

## 7. App data

```text
<home>/apps/my-app/data/
```

- Core preserves it on update and remove by default.
- The backup includes app data, not app code/venv.
- An app must own its migrations.

## 8. Example

`examples/hello-app` uses the SDK to write an item:

```text
POST /write
→ CoreClient.create_item()
→ Core /v1/items
```

Run its tests:

```bash
python -m unittest tests.test_loomsci_core_sdk
```

## 9. Rules

- Use only `/v1` or the SDK.
- Do not read another app's data.
- Do not write outside your data namespace.
- Do not depend on Core internals.
- Handle Core being down; do not crash silently.
- Keep secrets out of logs.
- On unsupported `core_api`, fail with a clear error.

## 10. Known gaps

- no third-party app marketplace
- no app CLI commands
- no production signed package layout
- no cross-app sharing
- no multi-user identity
- no automatic app migration
