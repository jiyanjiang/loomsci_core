# Contributing

Thanks for helping. This project is a preview seed; keep changes small and
reviewable.

## Ground rules

- Use Python 3.12 on macOS and Windows.
- Never commit credentials, tokens, private keys, real user data, or absolute
  user-home paths.
- Do not add a feature that is not in the current roadmap without an issue and
  an accepted design note.
- Keep user-facing text bilingual (`zh-CN` and `en`).

## Development setup

macOS:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Windows (PowerShell):

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If `requirements.txt` is empty, the preview has no runtime dependencies yet.

## Checks

Install the versioned pre-push hook once per clone:

```bash
python scripts/install_git_hooks.py
```

Every push then runs the mandatory sanitization check. Run the same checks
manually:

```bash
python scripts/check_public_tree.py
python -m unittest discover -s tests -v
```

The check rejects API keys, tokens, private keys, absolute user-home paths,
local databases, env files, and other content that must not be published.
A push without a passing check is not allowed.

## Pull requests

- One concern per pull request; explain the problem and the acceptance check.
- Include the commands you ran and their output.
- Do not reformat unrelated files.
- By contributing, you agree that your contribution is licensed under
  Apache-2.0.

## Bug intake

Record reproduced defects in [`bugs/`](bugs/README.md) with
`python scripts/buglog.py new` and include the exact input, expected/actual
output, surface, and evidence. Do not start a bug-fix batch until
`python scripts/buglog.py gate` reports at least 10 open reports.

## Security

See [SECURITY.md](SECURITY.md). Do not report vulnerabilities in public issues.
