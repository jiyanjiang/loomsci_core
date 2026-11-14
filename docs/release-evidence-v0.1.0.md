# Release evidence: v0.1.0

Status: **dual-platform gate passed** at commit `90975fe`.

Workflow: `.github/workflows/release-test.yml`
Run: `43579862388`
Result: both jobs completed successfully.

## macOS

- Runner: `macos-latest`, Python 3.12
- CI: **passed**
- Steps: items/search, backup/restore, CLI lifecycle, SDK items, SDK + App Host
- Local clean venv: 5 tests OK
- Local end-to-end smoke: `MINIMAL_SMOKE_OK`

## Windows

- Runner: `windows-latest`, Python 3.12
- CI: **passed**
- Steps: items/search, backup/restore, CLI lifecycle, SDK items, SDK + App Host

## Fixes found by the gate

- loopback health and SDK requests now bypass proxy environment variables
- Core startup allows up to 60 seconds
- App Host startup allows up to 90 seconds
- SDK app test allows slow app startup

## Remaining check

Independent documentation walkthrough by a person who did not write the code is
still recommended, but is not a release blocker for the minimal public beta.
