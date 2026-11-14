# LoomSci Core · Minimal v0

**Status: `0.1.0` minimal public beta. macOS and Windows release gates passed
at commit `90975fe`.**

A local-first substrate for one-owner apps. Core stores items, tags, blobs, and
search. Apps run separately and use the Core API through a scoped token.

The beta is for people who already have Python 3.12 and an AI IDE. It is not a
consumer installer and does not bundle Python.

## Requirements

- Python 3.12
- One AI IDE or terminal
- macOS or Windows

No installer, updater, Python bundle, or account is required.

## Run

```bash
python3.12 -m venv .venv
./.venv/bin/pip install -r requirements-core.txt
./.venv/bin/python -m loomsci_core --home ./core-home --port 8795 start
./.venv/bin/python -m loomsci_core --home ./core-home --port 8795 status
./.venv/bin/python -m loomsci_core --home ./core-home --port 8795 stop
```

The token is created at `core-home/local.token`. Treat it as a secret.

## First item

```bash
TOKEN=$(cat core-home/local.token)
curl -sS -X POST http://127.0.0.1:8795/v1/items \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"app":"hello","type":"hello.note","title":"Hello","body":"World"}'
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
installer, updater, signed distribution
migration
app update/remove CLI
marketplace, accounts, federation
legacy LoomSci beta features
```

## Documentation

- [Platform](docs/en/core-v0/platform.md)
- [Core API](docs/en/core-v0/core-api.md)
- [App developer](docs/en/core-v0/app-developer.md)
- [Core maintainer](docs/en/core-v0/core-maintainer.md)
- [OpenAPI](docs/openapi/core-v0.json)
- [Release process](docs/release-process.md)
- [Release evidence](docs/release-evidence-v0.1.0.md)
- [Pre-shrink backup](docs/backup.md)
- [Changelog](CHANGELOG.md)

## Test

```bash
python -m unittest discover -s tests -q
```
