# Core v0 API reference

- Base URL: `http://127.0.0.1:<port>`
- API version: `core/1`
- Auth: `Authorization: Bearer <token>`
- Public: `/v1/health`, `/v1/version`
- JSON only for write endpoints

## Error shape

```json
{"ok": false, "error": "error_code"}
```

| Error | HTTP | Meaning |
|---|---:|---|
| `unauthorized` | 401 | missing/invalid token |
| `json_required` | 400 | body is not a JSON object |
| `invalid app` / `invalid type` | 400 | bad app/type slug |
| `not_found` | 404 | item/blob/app missing |
| `forbidden` | 403 | scoped app tried another namespace |
| `tags_required` | 400 | tags endpoint needs a list |
| `target_exists` | 400 | restore target already exists |
| `backup_*` / `hash_mismatch` | 400 | backup validation failed |

## Health and version

### GET `/v1/health`

```json
{"ok": true, "api": "core/1", "schema": 1, "service": "core_v0"}
```

### GET `/v1/version`

```json
{"ok": true, "product": "loomsci_core", "version": "0.1.0", "api": "core/1"}
```

### GET `/v1/status`

Requires auth.

```json
{"ok": true, "items": 4, "tags": 7, "blobs": 2}
```

## Items

### POST `/v1/items`

```json
{
  "app": "report",
  "type": "report.note",
  "title": "PISA",
  "body": "# Markdown",
  "metadata": {"style": "research-perspective-0.1.0"},
  "tags": ["pisa", "science"],
  "id": "optional-caller-id"
}
```

- `title`/`body`/`metadata`/`tags` optional
- `id` optional; must be unique
- `app`/`type` are required
- max 8 tags; normalized to lowercase

Response `201`:

```json
{"ok": true, "item": {
  "id": "i-...", "app": "report", "type": "report.note",
  "title": "PISA", "body": "# Markdown", "metadata": {},
  "tags": [{"tag": "pisa", "source": "ai", "confidence": null}],
  "created_at": "...", "updated_at": "..."
}}
```

### GET `/v1/items`

Query:

```text
app, type, tag, limit (1..200), offset
```

### GET `/v1/items/<id>`

### PATCH `/v1/items/<id>`

Allowed fields: `title`, `body`, `metadata`.

### DELETE `/v1/items/<id>`

### POST `/v1/items/<id>/tags`

```json
{"tags": ["a", "b"], "source": "ai"}
```

Replaces tags.

### GET `/v1/tags?limit=100`

```json
{"ok": true, "tags": [{"tag": "pisa", "count": 3}]}
```

### GET `/v1/search?q=PISA&limit=50`

FTS over title/body/tags/app. A scoped app sees only its own app.

## Blobs

### POST `/v1/blobs`

```json
{
  "filename": "report.md",
  "content_type": "text/markdown",
  "content_base64": "IyBoZWxsbw==",
  "item_id": "i-..."
}
```

### GET `/v1/blobs/<id>`

Returns bytes with `Content-Disposition: attachment`.

### GET `/v1/blobs/<id>?inline=1`

Returns JSON with UTF-8 text (max 200,000 chars) and `truncated`.

## Backups

### GET `/v1/backups`

Lists backup directories with manifests.

### POST `/v1/backups`

Creates a data-only backup under `<home>/backups/` and returns `{name,path}`.

### POST `/v1/backups/restore`

```json
{"backup": "/path/to/backup", "target": "/path/to/new-home"}
```

- target must not exist
- hashes are verified before copying
- token is regenerated
- app code/venv are not restored

## Apps

### GET `/v1/apps`

### POST `/v1/apps/install`

```json
{"source": "/path/to/app"}
```

### POST `/v1/apps/<slug>/start`

### POST `/v1/apps/<slug>/stop`

### POST `/v1/apps/<slug>/update`

```json
{"source": "/path/to/app"}
```

### DELETE `/v1/apps/<slug>`

App data is preserved by default.

## Scoped app token

Apps receive `LOOMSCI_APP_TOKEN` and `LOOMSCI_CORE_URL` in the environment.
They send the token as `Authorization: Bearer`.

A scoped token:

- can create only items with its own `app`
- can list/get/update/delete only its own items
- can search/tag only its own namespace
- cannot use backup or app management endpoints
