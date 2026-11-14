# Release evidence: v0.1.1

Status: **docs-only patch, dual-platform release gate passed**.

## A machine (macOS)

- Artifact: `loomsci_core-0.1.1-8cd6eee.zip`
- SHA256: `81cb12e6c864a69438b3bcb3dd9e236863abfed4ca0b6211e36206b1796e7711`
- Clean extraction, Python 3.12 venv
- 5 tests OK
- CLI start/status/stop PASS
- `A_RELEASE_ARTIFACT_011_OK`

## B machine (Windows)

- Host: `taa-win` / `192.168.101.113`
- Python 3.12.9
- Archive SHA256 verified
- 5 tests OK
- CLI start/status/stop PASS
- App Host install/start/write/read PASS
- backup/restore PASS
- Windows README commands checked
- `ROUND1_WINDOWS_011_OK`

## Change from 0.1.0

Only documentation and version metadata:

- README Windows PowerShell commands
- platform docs Windows commands
- PowerShell first-item example
- `VERSION`, `pyproject.toml`, `loomsci_core.version`

No Core behavior change.
