# Release evidence: v0.2.0-rc.3

Status: pre-release candidate. Not a public-beta declaration.

Candidate code commit: `5d82a52` (`release: prepare 0.2.0-rc.3`).
Scope exception: user-authorized P0 content-lifecycle closure required by
[PRODUCT.md](../PRODUCT.md). No new product domain.

## Gate 1: source and package

```bash
python -m unittest discover -s tests -q          # 15 tests OK
python -m compileall -q loomsci_core examples tests
node --check loomsci_core/web/app.js
git diff --check
```

Package built from the candidate commit:

```text
loomsci_core-0.2.0-rc.3.zip
SHA256 11bfdc74be89b6b0335d6b06cbee4a9c3c10405ef036602711d5f85205e9bb4f
```

- `VERSION`, `pyproject.toml`, and `loomsci_core.version` agree:
  `0.2.0-rc.3` / `0.2.0rc3` / `0.2.0-rc.3`.
- Package hash verified on the Windows machine.
- Public tree scanned before commit; no token, private key, or private absolute
  path was added.

## Gate 2: A machine — macOS

Host: macOS 26.2, arm64, Python 3.12.13.

Fresh venv:

```text
.venv created from Python 3.12.13
Flask 3.1.3
cryptography 50.0.2
python -m unittest discover -s tests -q  -> 15 tests OK
```

PyPI DNS was unavailable on A during the test window. A wheelhouse was
downloaded on B and transferred to A; the fresh venv installed the requirements
offline from those wheels. No packages were copied from the A test environment.

Clean-home acceptance:

```text
CLI start / stop                          PASS
GET /v1/health                            schema=2
install examples/hello-app                PASS
start sdk-demo                            PASS
POST /v1/items                            PASS
GET /v1/items/<id>                        PASS
GET /v1/search?q=fresh                    PASS
POST /v1/backups                          PASS
GET / contains #trash-view and #item-view PASS
```

Real-browser (Chromium) acceptance at 1440x900:

```text
nav: content, tags, trash, site, tools, settings     PASS
item opens in center; detail rail hidden             PASS
workspace one column: 1188px; item view 980px        PASS
PDF iframe preview: 1; attachment card: 1            PASS
tag page rows: 2                                     PASS
trash row: 1; restore clears trash                   PASS
item count after restore: 2                          PASS
```

No page errors were observed.

## Gate 3: B machine — Windows

Host: Windows 10.0.19045.0, Python 3.12.9.

Fresh venv from requirements:

```text
Flask 3.1.3
cryptography 50.0.2
python -m unittest discover -s tests -q  -> 15 tests OK (4.434s)
```

Clean-home acceptance:

```text
CLI start / stop                          PASS
GET /v1/health                            schema=2
install examples/hello-app                PASS
start sdk-demo                            PASS
POST /v1/items                            PASS
GET /v1/items/<id>                        PASS
GET /v1/search?q=acceptance               1 match
POST /v1/backups                          PASS
GET / UI contains #trash-view/#item-view  HTTP 200 PASS
package SHA256 match                      PASS
```

## Dual-machine result

Both platforms ran the full 15-test suite and the clean-home write/read/search/
backup acceptance. macOS additionally ran the real-browser UI acceptance.
`DUAL_MACHINE_RC3_OK`.

## Rollback

Previous release: `v0.2.0-rc.2`.
Pre-release data backup:
`<core-home>/backups/backup-20261115T053911Z`.
Keep that tag and backup. A failed candidate must not be retagged; publish a new
candidate after the gate passes again.
