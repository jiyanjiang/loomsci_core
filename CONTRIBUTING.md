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

```bash
python scripts/check_public_tree.py
```

The check validates required files, bilingual pairs, and forbidden content
patterns. It must pass before a pull request.

## Pull requests

- One concern per pull request; explain the problem and the acceptance check.
- Include the commands you ran and their output.
- Do not reformat unrelated files.
- By contributing, you agree that your contribution is licensed under
  Apache-2.0.

## Security

See [SECURITY.md](SECURITY.md). Do not report vulnerabilities in public issues.
