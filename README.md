# loomsci_core

**Local-first workspace for your personal AI agent.**
Data stays yours. No login. Portable across machines and AI IDEs.

> **Preview seed.** This repository currently contains the specification,
> architecture, roadmap, and documentation skeleton. The first runnable
> preview release is pending. Nothing here should be read as a shipped feature.

[中文](README.zh-CN.md) · [Docs](docs/en/quickstart.md) · [Roadmap](docs/en/roadmap.md) · [Security](SECURITY.md) · [License](LICENSE)

## Why

- **Yours.** Projects, posts, tasks, memory, and attachments live on your disk.
- **No account.** One owner, one main agent (`alice` by default); no cloud dependency.
- **Portable.** Export everything as JSON + Markdown; switch IDEs or machines without losing context.

AI IDEs are the hands. `loomsci_core` is the memory, collaboration bus, and audit trail.

## How it fits

```text
AI IDE agents (Codex / Pi / opencode / CodeBuddy)
                 │  CLI / HTTP
                 ▼
        loomsci_core host            one port, loopback by default
        ├── posts / tasks / leases
        ├── memory / facts / artifacts
        └── local boundary + export
```

## Quickstart (preview)

The runnable installer is not available yet. The planned environment is
Python 3.12 on macOS and Windows.

macOS:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

Windows (PowerShell):

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
```

Dependencies will be finalized with the first preview release. The current
`requirements.txt` is intentionally empty.

## Status

| Area | Status |
|---|---|
| Public seed / docs | available |
| Core host + local API | in design |
| alice baseline | in design |
| macOS + Windows installation | in design |
| First preview release | pending |

## License

Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).

## Security

Please do not open public issues for vulnerabilities. See [SECURITY.md](SECURITY.md).
