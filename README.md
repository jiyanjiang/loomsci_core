# LoomSci Core · Minimal v0

**Status: `0.2.0-rc.3` release candidate. The Core Web UI is available at
`http://127.0.0.1:8795/`. P0 content lifecycle is complete: soft delete, trash,
restore, hard delete with blob cleanup, main-area item detail, app-scoped tags,
and attachment cards with PDF preview. Schema `v2` migrates existing databases
with a pre-migration backup. This is a pre-release, not a public-beta release.**

A local-first minimal core product for one owner. The authoritative product
definition is [PRODUCT.md](PRODUCT.md). Apps extend Core; they are not a
prerequisite for Core being usable.

The beta is for people who already have Python 3.12 and an AI IDE. It is not a
consumer installer and does not bundle Python.

## Requirements

- Python 3.12
- One AI IDE or terminal
- macOS or Windows

No installer, updater, Python bundle, or account is required.

## Run

macOS / Linux:

```bash
python3.12 -m venv .venv
./.venv/bin/pip install -r requirements-core.txt
./.venv/bin/python -m loomsci_core --home ./core-home --port 8795 start
./.venv/bin/python -m loomsci_core --home ./core-home --port 8795 status
./.venv/bin/python -m loomsci_core --home ./core-home --port 8795 stop
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements-core.txt
.\.venv\Scripts\python -m loomsci_core --home .\core-home --port 8795 start
.\.venv\Scripts\python -m loomsci_core --home .\core-home --port 8795 status
.\.venv\Scripts\python -m loomsci_core --home .\core-home --port 8795 stop
```

Open the Core UI:

```text
http://127.0.0.1:8795/
```

The token is created at `core-home/local.token` (`core-home\local.token` on
Windows). Treat it as a secret. CLI and SDK use it as a Bearer token; the Web UI
uses an HttpOnly SameSite=Strict cookie and never receives the token in HTML.

## First item

```bash
TOKEN=$(cat core-home/local.token)
curl -sS -X POST http://127.0.0.1:8795/v1/items \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"app":"hello","type":"hello.note","title":"Hello","body":"World"}'
```

Windows PowerShell:

```powershell
$TOKEN = Get-Content .\core-home\local.token
$body = '{"app":"hello","type":"hello.note","title":"Hello","body":"World"}'
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8795/v1/items `
  -Headers @{ Authorization = "Bearer $TOKEN" } `
  -ContentType "application/json" -Body $body
```

## Example app

With Core running:

```bash
TOKEN=$(cat core-home/local.token)
curl -sS -X POST http://127.0.0.1:8795/v1/apps/install \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"source":"./examples/hello-app"}'

curl -sS -X POST http://127.0.0.1:8795/v1/apps/sdk-demo/start \
  -H "Authorization: Bearer $TOKEN"

curl -sS -X POST http://127.0.0.1:8795/v1/items \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"app":"sdk-demo","type":"sdk-demo.note","title":"hello","body":"world"}'
```

The example uses `loomsci_core.sdk.CoreClient` and receives its scoped token from
the App Host.

## Minimal scope

In scope:

```text
items, tags, blobs, FTS search
local token and scoped app token
items/search/blob API
App Host install/start/stop
backup/restore
SDK
one example app
```

Out of scope for this version:

```text
installer, app auto-update, signed distribution
migration
app update/remove CLI
marketplace, accounts, federation
legacy LoomSci beta features
```

## Documentation

- [Help](docs/en/core-v0/help.md)
- [Update CLI](docs/en/core-v0/help.md#update)
- [Platform](docs/en/core-v0/platform.md)
- [Core API](docs/en/core-v0/core-api.md)
- [App developer](docs/en/core-v0/app-developer.md)
- [Core maintainer](docs/en/core-v0/core-maintainer.md)
- [OpenAPI](docs/openapi/core-v0.json)
- [Release process](docs/release-process.md)
- [0.2.0-rc.3 release notes](docs/release-notes-v0.2.0-rc.3.md)
- [0.2.0-rc.3 release evidence](docs/release-evidence-v0.2.0-rc.3.md)
- [Older release evidence](docs/release-evidence-v0.2.0.md)
- [UI asset migration](docs/ui-assets.md)
- [Pre-shrink backup](docs/backup.md)
- [Changelog](CHANGELOG.md)

## Test

```bash
python -m unittest discover -s tests -q
```
