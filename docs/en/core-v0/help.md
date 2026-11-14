# LoomSci Core 0.2.0-rc.1 — Help

## Start

```bash
python3.12 -m venv .venv
./.venv/bin/pip install -r requirements-core.txt
./.venv/bin/python -m loomsci_core --home ./core-home --port 8795 start
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements-core.txt
.\.venv\Scripts\python -m loomsci_core --home .\core-home --port 8795 start
```

Open `http://127.0.0.1:8795/`.

The Web UI uses an HttpOnly SameSite=Strict cookie. CLI and SDK use the bearer
token in `core-home/local.token`.

## Layout

```text
left rail: content / site / settings / CN-EN
center:    composer, search, tag cloud, item list
right:     selected item detail
```

## Content

- Write Markdown directly. There is no title field.
- Markdown headings, bold, code, tables, links, and KaTeX `$...$` / `$$...$$`
  render.
- Paste an image from the clipboard or choose files. A thumbnail is shown
  before publishing.
- Attachments are displayed with their SHA-256 short name.
- Click an item to open it in the right pane.
- Markdown attachments are rendered nested in the detail pane.
- Click an image thumbnail to open the gallery. Previous/next wraps around;
  Escape closes.

## Search and tags

- Search the body.
- The tag cloud shows the top 1000 tags with counts.
- Click a tag to filter; click it again to clear.
- The list loads 20 items at a time.

## Settings

- Username.
- DeepSeek API Key. It is stored locally only and is not sent to Core logs.
- Local fingerprint, generated locally and rotated every 30 days.
- Backup area: create, list, verify, and restore to a new empty directory.

Restore never overwrites the running home. The token is regenerated in the
restored workspace.

## Site

- Site name is shown in the left brand and document title.
- Logo URL is optional. Leave it blank to hide the logo.
- Supported logo URLs: `http://`, `https://`, or a path beginning with `/`.

## Data

```text
core-home/data/core.db
core-home/data/blobs/
core-home/apps/<slug>/data/
core-home/backups/
core-home/local.token
```

Schema version is `PRAGMA user_version = 1`. A pre-migration copy is created
before an older database is upgraded. A newer schema is rejected.

## API / SDK

- CLI and SDK: `Authorization: Bearer <local.token>`.
- Web UI: HttpOnly cookie set by `GET /`.
- API docs: [core-api](core-api.md), [OpenAPI](../../openapi/core-v0.json).

## Troubleshooting

- Port busy: choose another `--port`.
- UI does not connect: check `status`, then open `/v1/health`.
- Backup restore refused: the target directory must not exist.
- Future schema error: use the newer Core version, do not downgrade the data.

## Current limitations

- No automatic updater yet.
- No GitHub app installer yet.
- No Report app yet.
- No load/stress test yet.
- Windows is verified by tests, screenshots, and mouse clicks, but not by an
  independent external user walkthrough.
