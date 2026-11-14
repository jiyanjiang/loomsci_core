# Release process

No tag is a public beta until every gate below passes on the exact commit being
released. A local test run is not a dual-machine test.

## Gate 0: scope

- [ ] no new Core feature in the release
- [ ] only bug, docs, or release fixes since the candidate
- [ ] known exclusions are written down

## Gate 1: source checks

```bash
python -m unittest discover -s tests -q
python -m compileall -q loomsci_core examples tests
git diff --check
```

- [ ] tests pass
- [ ] `VERSION`, `pyproject.toml`, and `loomsci_core.version` agree
- [ ] public tree has no token, key, or absolute private path

## Gate 2: macOS clean test

Use an empty home and a fresh venv.

- [ ] create venv with Python 3.12
- [ ] install `requirements-core.txt`
- [ ] start Core
- [ ] install `examples/hello-app`
- [ ] start the app
- [ ] write, read, search an item
- [ ] create a backup
- [ ] stop Core

Record OS version, Python version, commands, and result.

## Gate 3: Windows clean test

Repeat Gate 2 in PowerShell on a separate Windows machine or VM.

- [ ] create venv with Python 3.12
- [ ] install `requirements-core.txt`
- [ ] start Core
- [ ] install `examples/hello-app`
- [ ] start the app
- [ ] write, read, search an item
- [ ] create a backup
- [ ] stop Core

Record OS version, Python version, commands, and result.

## Gate 4: docs walkthrough

- [ ] another person follows only `README.md` and `docs/`
- [ ] every command works as written
- [ ] failures are fixed or documented

## Gate 5: release

- [ ] release notes written
- [ ] pre-shrink backup exists
- [ ] dual-machine evidence attached
- [ ] tag created only after Gates 2 and 3 pass

## Rollback

Keep the previous tag and backup branch. If a release fails after tagging:

```bash
git tag -d <bad-tag>
git push origin :refs/tags/<bad-tag>
```

and publish a new candidate only after the gate passes again.
