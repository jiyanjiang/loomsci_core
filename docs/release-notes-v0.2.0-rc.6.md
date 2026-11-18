# LoomSci Core 0.2.0-rc.6 — path routes and robust updates

Status: pre-release candidate. Not a public-beta declaration.

## Changes

- Replaced hash routes with normal paths:
  `/version`, `/tags`, `/trash`, `/tools`, `/settings`, `/site`,
  `/item/<id>`, `/item/<id>/full`.
- Legacy `#/...` URLs are migrated to path URLs on load.
- Server serves the SPA shell for direct path loads.
- Update manifest fetch now uses the GitHub Contents API first, with raw
  fallback, a Loomsci user agent, and retries. Package download also retries.
- Built-in signed update source remains automatic; users do not configure it.
- Corrected trash text to actual behavior: items stay until restored or
  permanently deleted.
- Product/docs now list signed Core update in scope and remove stale
  "no updater" statements.

## TAA patterns adopted

- Path-based URLs instead of `#` fragments.
- API-first manifest read to avoid raw CDN cache/reset issues.
- Persistent update state and phase journal.
- Failed-version blocking and manual retry.
- Code + data rollback.

TAA collaboration rooms, agents, and executors are intentionally **not**
copied; Core remains single-owner and has no collaboration/executor layer.

## Gates

- [ ] source checks and full unit tests
- [ ] path-route browser regression without `#`
- [ ] update check via Contents API and raw fallback
- [ ] macOS/Windows fresh-package checks
- [ ] release package SHA256
- [ ] tag and push (only if requested)
