# loomsci_core

**Local-first workspace for your personal AI agent.**
Data stays yours. No login. Portable across machines and AI IDEs.

> **Preview seed.** This repository currently contains the specification,
> architecture, roadmap, and documentation skeleton. The first runnable
> preview release is pending. Nothing here should be read as a shipped feature.

[中文](README.zh-CN.md) · [Docs](docs/en/quickstart.md) · [Architecture](docs/en/architecture.md) · [Source map](docs/en/source-map.md) · [Release](docs/en/release.md) · [Roadmap](docs/en/roadmap.md) · [Security](SECURITY.md) · [License](LICENSE)

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

The preview currently declares Flask only. The minimal host can be run with
`python -m cli.loomsci serve`; the full installer is still pending.

## Status

| Area | Status |
|---|---|
| Public seed / docs | available |
| Core host + local API | minimal host + bus + handoff (S1.5) |
| alice baseline | available (S2) |
| Status UI | `/app` + read-only posts/tasks (S2–S3) |
| Export / import | zip round-trip (S3) |
| Release packaging | zip + manifests + SHA-256 (S4) |
| macOS installer | available and tested |
| Windows installer | script present; Windows CI run pending |
| First preview release | pending |

Every push runs a mandatory sanitization check (API keys, tokens, absolute
user-home paths, local data files). See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).

## Security

Please do not open public issues for vulnerabilities. See [SECURITY.md](SECURITY.md).
