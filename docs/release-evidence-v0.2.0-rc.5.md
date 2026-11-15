# Release evidence: v0.2.0-rc.5

Status: pre-release candidate. Not a public-beta declaration.
Scope: Version page, signed update check/download, persistent journal, data
rollback, failed-version blocking.

Candidate code commit: `c6e7cf4`.

## Package

```text
loomsci_core-0.2.0-rc.5.zip
SHA256 ebddd61012d2e0b0b87dbc13824a18b248399aa45e7adf46c8d5f09153ec0ab6
```

## Source checks

```text
node --check loomsci_core/web/app.js
python -m unittest discover -s tests -q          # 16 tests OK
python -m compileall -q loomsci_core examples tests
python -m json.tool docs/openapi/core-v0.json
git diff --check
```

## A machine — macOS 26.2 / Python 3.12.13

- fresh venv: Flask 3.1.3, cryptography 50.0.2; `16/16` unit tests pass.
- Version page is a separate left-nav menu, not part of Settings.
- Default state: current `0.2.0-rc.5`, latest `—`, status
  `Update source not configured`, source `—`, check time `—`.
- Check with no source returns `no_manifest_url`; UI says
  `Update source not configured` (not "Up to date", not a signature error).
- With a signed local test manifest configured: latest `0.2.0-rc.6`,
  check/download succeed, install button enabled, state `downloaded`.
- End-to-end update: rc.5 -> rc.6; server restarted; `/v1/version` reports
  `0.2.0-rc.6`; pre-update item remains searchable.
- End-to-end rollback: deliberately broken rc.6 package; apply exits non-zero;
  Core returns as rc.5; item survives; journal `ROLLED_BACK`.

## B machine — Windows 10.0.19045 / Python 3.12.9

- fresh venv: Flask 3.1.3, cryptography 50.0.2; `16/16` unit tests pass
  (`4.756s`).
- Exact rc.5 package: Version menu present; current `0.2.0-rc.5`; latest `—`;
  status `未配置更新源`; source/check time/journal `—`; no update block in
  Settings.
- End-to-end update: rc.5 -> rc.6; server restarted; pre-update item searchable.
- End-to-end rollback: deliberately broken rc.6 package; Core returns as rc.5;
  pre-update item survives; journal `ROLLED_BACK`.
- Package SHA256 verified before extraction.

## Root cause of the earlier `manifest signature missing`

The old default update URL pointed at a remote `latest.json` for
`0.1.0-beta.28` whose `signature` field was empty. That stale manifest was
therefore invalid. The default source is now empty; the Version page reports
`Update source not configured`, and a source must be configured explicitly.
The legacy URL is also normalized away from existing local update state.

## Notes

- End-to-end tests use a generated Ed25519 test key via
  `LOOMSCI_UPDATE_PUBLIC_KEY`; the production private key is not in the
  repository. No production update channel/manifest was published.
- Automatic check/download is wired into `server.main`; the six-hour timer was
  not soak-waited. Manual check/download and the detached install path were
  exercised.
- Automatic installation is intentionally not enabled; downloaded updates
  require an explicit **Install and restart** click.

## Result

`DUAL_MACHINE_RC5_VERSION_PAGE_OK`.

No new tag or push was performed for this candidate.
