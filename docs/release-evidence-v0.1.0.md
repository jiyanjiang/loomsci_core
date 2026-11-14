# Release evidence: v0.1.0

Status: **not a valid public beta**.

The `v0.1.0` tag was created before the release gates in
[release-process](release-process.md) were executed. It must not be treated as a
public beta.

## macOS

- Machine: this Mac (darwin arm64)
- Python: 3.12 project venv
- Clean venv install: `CLEAN_MACOS_OK`
- Tests in clean venv: `Ran 4 tests ... OK`
- End-to-end smoke: `MINIMAL_SMOKE_OK`
- Covered: Core start, app install, app start, item write, search, backup,
  app stop

## Windows

- Status: **CI gate added; result not yet observed**
- Workflow: `.github/workflows/release-test.yml` (`windows-latest`, Python 3.12)
- Required before a public beta tag: green Windows run plus the smoke path

## Consequence

The tag is a candidate only. Do not announce it as public beta until Windows
passes and both results are recorded here.

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
