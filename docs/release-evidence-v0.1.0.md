# Release evidence: v0.1.0

Status: **not a valid public beta**.

The `v0.1.0` tag was created before the release gates in
[release-process](release-process.md) were executed. It must not be treated as a
public beta.

## macOS

- Machine: this Mac (darwin arm64)
- Python: 3.12 project venv
- Clean venv install: `CLEAN_MACOS_OK`
- Local clean venv: 5 tests OK
- End-to-end smoke: `MINIMAL_SMOKE_OK`
- CI (`macos-latest`): **failed** in run 43577546690; test file is being isolated
- Covered locally: Core start, app install, app start, item write, search, backup,
  app stop

## Windows

- CI (`windows-latest`, Python 3.12): **passed** in run 43577546690
- Workflow: `.github/workflows/release-test.yml`
- Evidence: 5 tests OK, including CLI lifecycle, App Host, SDK, backup/restore

## Consequence

The tag is a candidate only. Do not announce it as public beta until both
macOS and Windows CI are green and the results are recorded here.

## Minimum evidence to add

```text
Windows version:
Python version:
Core start result:
App install result:
App start result:
Item write/search result:
Backup result:
Core stop result:
```
