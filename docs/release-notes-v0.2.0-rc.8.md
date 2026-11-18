# LoomSci Core 0.2.0-rc.8 — app origin isolation and update lock

Status: pre-release candidate. Not a public-beta declaration.

## Changes

- Apps open on `http://app-<slug>.localhost:<core-port>/apps/<slug>/`.
- Core-origin `/apps/<slug>/` redirects to the isolated app origin.
- App proxy no longer forwards owner Cookie/Authorization/X-LoomSci-Token and
  no longer mints the Core UI session on the app origin.
- Update install uses a cross-process lock; duplicate apply requests are
  rejected. The install button disables while applying.
- Full item view is left-aligned with a 16px gutter.
- Windows dual-host testing remains deferred.

## Gates

- [x] source checks and full unit tests
- [x] app origin cookie/localStorage isolation
- [x] update lock
- [x] macOS browser layout/path/update regression
- [x] package SHA256
- [x] tag and push: v0.2.0-rc.8

Evidence: [release evidence](release-evidence-v0.2.0-rc.8.md).
