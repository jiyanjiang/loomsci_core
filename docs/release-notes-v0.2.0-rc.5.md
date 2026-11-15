# LoomSci Core 0.2.0-rc.5 — version and safe update

Status: pre-release candidate. Not a public-beta declaration.

## Changes

- Added `/v1/version` display in the left rail and a dedicated Version page.
- No update source is configured by default. The Version page shows the local
  version and **Update source not configured** instead of a stale manifest
  error. A signed manifest URL can be configured explicitly.
- Added signed update check/download with persistent state at
  `<home>/updates/update.json`.
- Added background check/download; checks run after startup and at most every
  six hours. Installation remains manual by default.
- Added update phase journal at `<home>/updates/journal.json`.
- Added failed-version blocking with manual retry.
- Update rollback now restores both code and data from the pre-update backup.
- Added `update status|check|download|install|settings` CLI commands and
  `/v1/update/status|check|download|apply|settings` API endpoints.
- Package/manifest contract: `product`, `version`, `channel`, `url`, `sha256`,
  `min_core`, `notes_url`, Ed25519 `signature`.

## Upgrade notes

- Existing homes keep their data; update state is additive.
- The updater stops Core before taking the data backup, so the backup represents
  the stopped state.
- A failed update restores the old code and the pre-update database/blob/app
  data, then starts Core.
- Automatic installation is not enabled; downloaded updates require an explicit
  **Install and restart** click.

## Gates

- [x] source checks and full unit tests
- [x] macOS update end-to-end with a signed test release
- [x] Windows update end-to-end with a signed test release
- [x] browser version/update card acceptance on both machines
- [x] release package SHA256
- [ ] tag and push (only if requested)

Evidence: [release evidence](release-evidence-v0.2.0-rc.5.md).
