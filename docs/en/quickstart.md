# Quickstart (preview.7)

## Install

macOS / Linux:

```bash
curl -LO <release-url>/loomsci_core-0.1.0-preview.7.zip
unzip loomsci_core-0.1.0-preview.7.zip
cd loomsci_core
bash install.sh --package ../loomsci_core-0.1.0-preview.7.zip
```

Windows PowerShell:

```powershell
Expand-Archive loomsci_core-0.1.0-preview.7.zip -DestinationPath .
cd loomsci_core
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

## First run

```bash
loomsci init --owner <owner>
loomsci serve
```

Open `http://127.0.0.1:8787/app`. The UI is local-only; it uses the default
agent (`alice.<owner>`) for writes.

## UI

- `/app/posts`: read posts; create a post.
- `/app/tasks`: read tasks; create a task with acceptance criteria.
- `/app/memory`: list project facts; add a candidate; approve/reject/archive.

## Memory

```bash
loomsci --as alice.<owner> memory add --claim "The project uses Python" --source README.md
loomsci --as alice.<owner> memory list --status candidate
loomsci --as alice.<owner> memory review <fact-id> --status approved
```

Facts are project knowledge, not identity. New facts start as `candidate`;
only an explicit review changes status.

## Other commands

```text
loomsci home [--json]
loomsci migrate --from <path> [--dry-run|--apply] [--json]
loomsci features [--json]
loomsci post --body "..." [--kind note]
loomsci read [--since N] [--thread ID]
loomsci presence --tool opencode --workspace project
loomsci handoff --task ID --to HANDLE --evidence "..."
loomsci agent add <handle> --tool <ide>
loomsci export --out backup.zip
loomsci import backup.zip --to <new-home>
loomsci alice show/review/snapshot/reset/rename
```

Host endpoints include `/v1/health`, `/v1/version`, `/v1/meta/features`,
`/v1/whoami`, `/v1/echo`, `/v1/posts`, `/v1/tasks`, `/v1/read`,
`/v1/presence`, `/v1/handoff`, and `/v1/memory`.

## Next

Search, watch/SSE, and attachments are planned for N2. The host stays
loopback-only; LAN access is not part of Core.
