# LoomSci Core 0.2.0-rc.5 — Help

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
left rail: content / tags / trash / site / tools / settings / CN-EN
center:    composer, search, tag cloud, item list, full item
right:     selected item preview; hidden in full item mode
```

## Content

- Write Markdown directly. There is no title field.
- Markdown headings, bold, code, tables, links, and KaTeX `$...$` / `$$...$$`
  render.
- Paste an image from the clipboard or choose files. A thumbnail is shown
  before publishing.
- Attachments use file cards with type icon, MIME, size, open, and download.
  PDFs preview inline; Markdown attachments render nested in the detail view.
- Click an item to preview it in the right rail. The center list does not move
  and keeps its scroll position.
- **Open full** expands the item into the center; the list and right rail are
  hidden. **← Back** returns to the preview and restores the list position.
- **Back to list** clears the preview without changing the list position.
- Click an image thumbnail to open the gallery. Previous/next wraps around;
  Escape closes.
- Delete moves an item to Trash. Restore returns it; permanent delete removes
  its blobs from disk.

## Search and tags

- Search the body and titles; trashed items are excluded.
- The tag cloud shows the top 20 tags with counts; **All tags** opens a
  searchable tag page.
- Item cards show at most 3 tags plus `+N`; the full list is on the item detail
  and tag page.
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

## Backup and restore

### What a backup contains

```text
data/core.db
data/blobs/
apps/<slug>/data/
```

It does not contain:

```text
local.token
Core code
venv
logs
```

### Create

1. Open Settings in the left rail.
2. Find the Backups area.
3. Click Create backup.
4. A `backup-YYYYMMDDTHHMMSSZ` entry appears.

Backups live under:

```text
core-home/backups/
```

### Verify

Click Verify on a backup row. A valid backup shows "Backup verified".
A missing manifest or hash mismatch is rejected.

### Restore

A restore must target a **new, empty directory**. It never overwrites the
running workspace.

In Settings:

1. Enter `/tmp/loomsci-restored` as the restore target.
2. Click Restore on a backup row.
3. Start the restored workspace:

```bash
python -m loomsci_core --home /tmp/loomsci-restored --port 8796 start
```

4. Open `http://127.0.0.1:8796/`.

Windows:

```powershell
.\.venv\Scripts\python -m loomsci_core --home C:\Users\you\loomsci-restored --port 8796 start
```

The restored workspace gets a new `local.token`. Do not restore over the running
`core-home`.


```text
core-home/data/core.db
core-home/data/blobs/
core-home/apps/<slug>/data/
core-home/backups/
core-home/local.token
```

Schema version is `PRAGMA user_version = 2`. A pre-migration copy is created
as `core.db.pre-v2-*` before an older database is upgraded. A newer schema is
rejected.

## Update

## Tools catalog

## App URLs and one-port access

Apps run in isolated processes, but the browser uses the Core origin:

```text
http://127.0.0.1:8795/apps/<slug>/
```

Core proxies `/apps/<slug>/` to the app's internal loopback port. The internal
port is implementation detail and is not shown in the UI.


Open `#/tools`, enter a catalog JSON URL or local path, then click Detect.

```json
{
  "format": "loomsci-catalog/1",
  "apps": [
    {
      "slug": "report",
      "name": "LoomSci Report",
      "version": "0.1.0",
      "repo": "https://github.com/example/loomsci-report",
      "description": "Research report generator"
    }
  ]
}
```

A local `source` path is accepted for development. A `repo` must be an
`https://github.com/` URL. Install uses the existing App Host and does not run
the app automatically.


The rail shows the running version. The **Version** page shows current version,
latest version, the built-in signed update source, and install state. Users do
not configure a manifest URL.

```text
notify   check only
download check, download, notify (default)
```

Core checks in the background after startup and at most every six hours. Updates
are downloaded and verified automatically; installation stays manual by default.

```bash
python -m loomsci_core update status
python -m loomsci_core update check [manifest.json]
python -m loomsci_core update download [manifest.json]
python -m loomsci_core update install
python -m loomsci_core update settings --mode download
python -m loomsci_core update apply <manifest.json> --package <payload.zip>
```

The manifest must be HTTPS (or local in tests), signed with Ed25519, and include
`product`, `version`, `min_core`, `sha256`, `url`, and `signature`. Apply stops
Core, creates a data backup and code snapshot, swaps the package, starts Core,
and restores both code and data on failure. Update state is persisted in
`<home>/updates/update.json`; the phase journal is
`<home>/updates/journal.json`. A failed version is blocked from automatic
retry; a manual retry is allowed. The public key is
`loomsci_core/update_public_key.pem`.

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

- Automatic installation is not enabled by default; downloaded updates require
  a manual **Install and restart** click.
- No GitHub app installer yet.
- No Report app yet.
- No load/stress test yet.
- Windows is verified by tests, screenshots, and mouse clicks, but not by an
  independent external user walkthrough.
