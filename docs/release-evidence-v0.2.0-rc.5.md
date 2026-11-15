# Release evidence: v0.2.0-rc.5

Status: pre-release candidate. Not a public-beta declaration.
Scope: dedicated Version page, automatic signed update source, update
check/download, persistent journal, data rollback, failed-version blocking.

Candidate code commit: `895b9b4`.
Release channel commit: `b554606`.

## Published channel

```text
manifest: https://raw.githubusercontent.com/jiyanjiang/loomsci_core/minimal-v0/releases/latest.json
package:  https://raw.githubusercontent.com/jiyanjiang/loomsci_core/minimal-v0/releases/loomsci_core-0.2.0-rc.5-final.zip
version:  0.2.0-rc.5
SHA256:   67f0f6b52ba1b4c1d9b2d2fa96d7ebf4d39e0b45ab0de23241cef3b59ce7ebfb
bytes:    389618
```

The manifest is signed with the Core Ed25519 key whose public half is
`loomsci_core/update_public_key.pem`; the private key is not in the repository.
The manifest and package are tracked on the `minimal-v0` branch. The update
source is built into Core; users do not configure it.

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
- Version is a dedicated left-nav page; Settings has no update block.
- Version page displays current `0.2.0-rc.5`, latest `0.2.0-rc.5`, automatic
  source, check time, journal, and **Up to date** after check.
- The source input is readonly; no user configuration is required.
- With a signed local test manifest: latest `0.2.0-rc.6`, check/download
  succeed, install button enabled.
- End-to-end update: rc.5 -> rc.6; server restarted; `/v1/version` reports
  `0.2.0-rc.6`; pre-update item remains searchable.
- End-to-end rollback: deliberately broken rc.6 package; apply exits non-zero;
  Core returns as rc.5; item survives; journal `ROLLED_BACK`.

## B machine — Windows 10.0.19045 / Python 3.12.9

- fresh venv: Flask 3.1.3, cryptography 50.0.2; `16/16` unit tests pass
  (`4.681s`/`4.756s`).
- Version menu present; current `0.2.0-rc.5`; automatic source URL shown;
  check returns latest `0.2.0-rc.5`, state `current`.
- End-to-end update: rc.5 -> rc.6; server restarted; pre-update item searchable.
- End-to-end rollback: deliberately broken rc.6 package; Core returns as rc.5;
  item survives; journal `ROLLED_BACK`.
- Package SHA256 verified before extraction.

## Root cause of the earlier `manifest signature missing`

The old default URL pointed at `main/releases/latest.json` for
`0.1.0-beta.28` with an empty `signature`. That stale manifest was invalid. It
has been replaced by the signed `minimal-v0` channel above, and the built-in
source now points there automatically. The legacy URL is normalized away from
existing local update state.

## Notes

- End-to-end update/rollback tests use a generated Ed25519 **test** key; the
  published rc.5 manifest uses the production Core key. No test private key is
  committed.
- Background check/download is wired into `server.main`; the six-hour timer was
  not soak-waited. Manual check/download and the detached install path were
  exercised.
- Automatic installation is intentionally not enabled; downloaded updates
  require an explicit **Install and restart** click.

## Result

`DUAL_MACHINE_RC5_VERSION_PAGE_OK`.
