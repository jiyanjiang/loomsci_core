# Changelog

## 0.2.0-rc.8 — app origin isolation and update lock

- Apps open on isolated `app-<slug>.localhost` origins; Core-origin app paths redirect there.
- App proxy strips owner cookies/Authorization and no longer mints the UI session.
- Update install uses a cross-process lock; duplicate apply requests are rejected.
- Full item view is left-aligned with a 16px gutter instead of centered.

## 0.2.0-rc.7 — resilient package download

- Update package download retries raw GitHub failures and falls back to the
  GitHub Contents API for versioned release files.
- Partial packages are removed before retry/fallback.
- Keeps path routes, API-first manifest checks, built-in signed updates, and
  code+data rollback.

## 0.2.0-rc.6 — path routes and robust updates

- Replaced `#/...` SPA routes with normal history paths.
- Added server-side SPA path fallbacks and legacy hash migration.
- Update manifest fetch uses GitHub Contents API first, raw fallback, retries,
  and a Loomsci user agent.
- Package download retries transient connection failures.
- Built-in signed update source remains automatic.
- Aligned product/docs with signed Core update in scope.
- Corrected trash wording to actual restore/permanent-delete behavior.

## 0.2.0-rc.5 — version and safe update

- Added `/v1/version`, a rail version label, and a dedicated Version page.
- Added signed update check/download with persistent `updates/update.json`.
- Added automatic background check/download; manual install is the default.
- Added update journal phases (`PREFLIGHT` through `COMMITTED`/`ROLLED_BACK`).
- Failed versions are blocked from automatic retry; manual retry is possible.
- Update rollback now restores both code **and data** from the pre-update backup.
- Added `update status|check|download|install|settings` CLI commands.
- Added `/v1/update/status|check|download|apply|settings` API endpoints.

## 0.2.0-rc.4 — TAA-style item preview

- Item click now opens a compact preview in the right rail; the center list
  stays in place and keeps its scroll position.
- Added **Open full** in the preview toolbar. Full mode expands the item into
  the center and hides the list and right rail.
- Added **← Back** from full mode; it returns to the preview and restores the
  prior list scroll position. **Back to list** clears the preview.
- Selected list items are highlighted.
- Narrow layouts skip the preview and open the item full width.

## 0.2.0-rc.3 — P0 content lifecycle and main-area UI

- Added soft delete, trash, restore, and hard delete with blob cleanup.
- Added schema v2 migration for `items.deleted_at`; existing databases are
  copied to `core.db.pre-v2-*` before migration.
- Excluded trashed items from lists, search, tag counts, and tag pages.
- Added app-scoped tag counts in SQL, removing the N+1 filter.
- Open item detail in the main center panel; the right rail is hidden and the
  workspace becomes one column.
- Tag cloud shows the top 20 tags plus a full, searchable tag page; item cards
  show at most 3 tags plus `+N`.
- Added unified attachment cards with type icon, MIME, size, open/download, and
  inline PDF preview.
- Blob downloads now stream through `send_file`; uploads are capped at 50 MB.
- Added `GET /v1/trash`, `POST /v1/trash/purge`, and item restore/delete routes.

## 0.2.0-rc.2 — signed update mechanism

- Added Ed25519-signed update manifest verification.
- Added `update check` and `update apply` CLI.
- Update apply backs up data, snapshots code, swaps the package, starts Core,
  and rolls back on failure.
- Added `cryptography` to Core requirements.
- Added update rollback test.

## 0.2.0-rc.1 — Core UI / P0 pre-release

- Three-column Core UI: navigation, list, detail.
- Markdown and KaTeX rendering; nested Markdown attachments.
- Clipboard image paste with thumbnail preview, SHA-256 attachment names.
- Unified thumbnails and looped gallery.
- Top-1000 tag cloud and tag filtering; 20-item pagination.
- Settings, site name/logo, CN/EN switch.
- HttpOnly SameSite=Strict UI session.
- Schema version 1 with pre-migration backup.
- Backup verify and restore-to-empty-directory UI.
- Windows mouse-click, gallery, tag, and settings acceptance.

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
