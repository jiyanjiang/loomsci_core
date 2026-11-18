# LoomSci Core 0.2.0-rc.7 — resilient package download

Status: pre-release candidate. Not a public-beta declaration.

## Changes

- Package download now retries raw GitHub failures and falls back to the
  GitHub Contents API for versioned release files.
- `raw.githubusercontent.com` connection resets no longer leave a partial
  package: the partial file is deleted before retry/fallback.
- Keeps the rc.6 path routing, API-first manifest check, built-in signed update
  source, version page, and code+data rollback.

## TAA boundary

Adopted from TAA: path URLs, API-first manifest reads, persistent update state,
phase journal, failed-version blocking, manual retry, data rollback.
Not adopted: collaboration rooms, agent coordination, executors.

## Gates

- [ ] source checks and full unit tests
- [ ] live update check via Contents API
- [ ] package download/verify through raw or API fallback
- [ ] macOS browser path/update regression
- [ ] release package SHA256
- [ ] tag and push (only if requested)
