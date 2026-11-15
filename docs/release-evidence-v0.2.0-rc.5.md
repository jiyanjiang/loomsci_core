# Release evidence: v0.2.0-rc.5

Status: pre-release candidate. Not a public-beta declaration.
Scope: version surface, signed update check/download, persistent journal, data
rollback, failed-version blocking, settings update card.

Candidate code commit: `18c244d`.

## Package

```text
loomsci_core-0.2.0-rc.5.zip
SHA256 c36a6f9dad15d41468e37ff8a8a0eb47bf99c74d0c95e1ca7f836cfc54b20075
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

- fresh venv: Flask 3.1.3, cryptography 50.0.2.
- `16/16` unit tests pass.
- Browser: rail shows `0.2.0-rc.5`; Settings update card shows current
  version, `download` mode, manifest URL, check/download/install controls;
  install disabled until a package is downloaded.
- UI check/download with a signed local test release: available `0.2.0-rc.6`,
  download completes, install button enabled.
- End-to-end update: rc.5 -> rc.6, server restarted, `/v1/version` reports
  `0.2.0-rc.6`, pre-update item is still searchable.
- End-to-end rollback: deliberately broken rc.6 package; apply exits non-zero;
  Core returns as rc.5; pre-update item survives; journal is `ROLLED_BACK`.

## B machine — Windows 10.0.19045 / Python 3.12.9

- fresh venv: Flask 3.1.3, cryptography 50.0.2.
- `16/16` unit tests pass (`4.663s`).
- Browser: exact rc.5 package shows rail version `0.2.0-rc.5`; Settings update
  block is present with current version, `download` mode, manifest URL, and
  install disabled.
- End-to-end update: rc.5 -> rc.6, server restarted, pre-update item searchable.
- End-to-end rollback: deliberately broken rc.6 package; Core returns as rc.5;
  pre-update item survives; journal is `ROLLED_BACK`.
- Package SHA256 verified before extraction.

## Notes

- The end-to-end tests use a generated Ed25519 test key via
  `LOOMSCI_UPDATE_PUBLIC_KEY`; the production private key is not in the
  repository. No production update channel/manifest was published.
- Automatic check/download scheduler is wired into `server.main`; the six-hour
  timer was not soak-waited. Manual check/download and the detached install
  path were exercised.
- Automatic installation is intentionally not enabled; downloaded updates
  require an explicit **Install and restart** click.

## Result

`DUAL_MACHINE_RC5_UPDATE_OK`.

No new tag or push was performed for this candidate.
