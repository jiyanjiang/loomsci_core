# LoomSci Core 0.2.0-rc.5 — version and safe update

Status: pre-release candidate. Not a public-beta declaration.

## Changes

- Added `/v1/version` display in the left rail and a Settings update card.
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

- [ ] source checks and full unit tests
- [ ] macOS update end-to-end with a signed test release
- [ ] Windows update end-to-end with a signed test release
- [ ] browser version/update card acceptance on both machines
- [ ] release package SHA256
- [ ] tag and push (only if requested)
