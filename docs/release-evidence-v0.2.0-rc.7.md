# Release evidence: v0.2.0-rc.7

Status: technical-user private beta. Not a public-beta declaration.
Release scope: path routes, API-first update checks, package download fallback,
App proxy credential isolation, version page, documentation alignment.

## Release point

```text
tag:     v0.2.0-rc.7
code:    35eb569
package: loomsci_core-0.2.0-rc.7-final.zip
SHA256:  4fe2276133c65ca952893c87ffb03bffa4b17d96c8a51451b2ae06c64b04ada8
bytes:   390861
```

The package is signed with the Core Ed25519 key whose public half is
`loomsci_core/update_public_key.pem`. The private key is not committed.

## Single-host gate

Per current instruction: single-host pass is accepted; Windows dual-host is
deferred by one week.

- macOS 26.2 arm64, Python 3.12.13.
- `17/17` unit tests pass.
- `node --check`, `compileall`, OpenAPI JSON, `git diff --check` pass.
- Fresh Core:
  - `/v1/version` = `0.2.0-rc.7`;
  - App navigation empty;
  - `/version` loads with no `#`;
  - update source is the built-in GitHub Contents API;
  - check returns current/latest `0.2.0-rc.7`.
- Browser:
  - `/version`, `/item/<id>`, `/item/<id>/full` have empty `location.hash`;
  - preview, full view, back, and browser back work.
- App proxy test:
  - owner `Cookie`, `Authorization`, and `X-LoomSci-Token` are not forwarded;
  - App-owned cookies remain.
- Update channel:
  - manifest signature and package SHA256 verify;
  - GitHub API first, raw fallback, package API fallback configured.

## TAA boundary

Adopted: path URLs, API-first manifest, update state machine/journal, failed
version blocking, code+data rollback, retry/fallback.

Not adopted: collaboration rooms, agent scheduling, executors, task system,
`#tag` presentation, feed/moments/inbox structures.

## Known gaps

- App and Core remain same-origin; app JavaScript can still read same-origin
  localStorage (including the DeepSeek key). Origin isolation is still needed
  before public beta.
- Update apply has no cross-process lock; concurrent apply remains a risk.
- Windows dual-host test deferred.
- CI still needs the full suite plus browser smoke and soak.

## Forum backup

Posted to `#projects/team-ai`: `p-880e001a`.
