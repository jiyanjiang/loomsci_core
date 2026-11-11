# loomsci_core

**Local-first workspace for your personal AI agent.**
Data stays yours. No login. Portable across machines and AI IDEs.

> **Preview.** `v0.1.0-preview.40` is the current local preview; it is not a production release.

[中文](README.zh-CN.md) · [Docs](docs/en/quickstart.md) · [Architecture](docs/en/architecture.md) · [Source map](docs/en/source-map.md) · [Testing](docs/en/testing.md) · [Core contract](docs/en/core-contract.md) · [Add-ons](docs/en/addons.md) · [Backup](docs/en/backup.md) · [N4 acceptance](docs/en/n4-acceptance.md) · [Release](docs/en/release.md) · [Roadmap](docs/en/roadmap.md) · [Security](SECURITY.md) · [License](LICENSE)

## Why

- **Yours.** Projects, posts, tasks, memory, and attachments live on your disk.
- **No account.** One owner, one main agent (`alice` by default); no cloud dependency.
- **Portable.** Export everything as JSON + Markdown; switch IDEs or machines without losing context.

AI IDEs are the hands. `loomsci_core` is the memory, collaboration bus, and audit trail.

## How it fits

```text
AI IDE agents (WorkBuddy / opencode / other local IDEs)
                 │  CLI / HTTP
                 ▼
        loomsci_core host            one port, loopback by default
        ├── posts / tasks / leases
        ├── memory / facts / artifacts
        └── local boundary + export
```

## Quickstart (preview)

Install from the preview package, then initialize and start the local host.

macOS:

```bash
bash install.sh --package loomsci_core-0.1.0-preview.40.zip
loomsci init --owner <name>
loomsci serve
```

Windows PowerShell:

```powershell
.\install.ps1 -Package .\loomsci_core-0.1.0-preview.40.zip
loomsci init --owner <name>
loomsci serve
```

Open `http://127.0.0.1:8787/app`. The host binds loopback; there is no login.

## Status

| Area | Status |
|---|---|
| Core host / local API | available |
| UI | posts, tasks (claim/done), memory review, inbox, attachments |
| Search / watch / export / import | available |
| macOS installer | tested |
| Windows installer | tested (L0-L6) |
| Real IDE | macOS opencode + omp passed; Windows dual-IDE waived |
| Release | local unsigned package; no GitHub Release |

Every push runs a mandatory sanitization check (API keys, tokens, absolute
user-home paths, local data files). See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).

## Security

Please do not open public issues for vulnerabilities. See [SECURITY.md](SECURITY.md).
