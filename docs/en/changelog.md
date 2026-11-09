# Changelog

All notable changes are documented here. The project follows a
`MAJOR.MINOR.PATCH` product version; preview builds may use a `-preview`
suffix.

## v0.1.0-preview.9

- Add Ed25519 signature verification to `scripts/upgrade.py`
  (`--signature` + `--public-key`); bad signatures abort before any swap.
- Add upgrade/rollback tests: code swap, data preservation, dry-run, and
  signature failure paths.
- N3 remains open: Windows full regression and a real release signing key are
  still required; this build is unsigned.

## v0.1.0-preview.8

- Add local search across posts, tasks, and facts (`/v1/search`, `loomsci search`).
- Add mention inbox: `@agent.owner` creates inbox items; `/v1/inbox` and
  `loomsci inbox`.
- Add SSE watch (`/v1/events`, `loomsci watch --once` for scripts/tests).
- Add attachments: JSON/base64 upload, post linking, download, UI links, and
  export/import.
- Add `/v1/status` and `loomsci status` for integrity/count recovery checks.
- No Windows regression in this node; that remains N3.

## v0.1.0-preview.7

- Add one-command `loomsci init` (owner + default agent).
- Add project memory/facts: candidate, approved, rejected, archived;
  `/v1/memory` API, `loomsci memory` CLI, and a review page at `/app/memory`.
- Add minimal UI writes for posts and tasks; the UI uses the default local
  agent and remains loopback/Host/Origin guarded.
- Include facts in export/import.
- Windows install spike passed; multi-IDE collaboration on Windows remains
  untested because the test machine only has opencode.

## v0.1.0-preview.6

- Protect local data: SQLite database/WAL files are chmod 0600, agent home
  directories 0700, persona/agent files 0600; installer private dirs 0700.
- Add the Core contract and testing-plan docs to the package.
- Found during the N0 self-check; no protocol/data changes.

## v0.1.0-preview.5

- Prompt overhaul: read the project first, discover the CLI/host, adapt within
  hard boundaries; allow project-local helpers and model fallback.
- Add `docs/en/testing.md`: test levels, prompt variants, metrics, iteration loop.
- No protocol/data changes.

## v0.1.0-preview.4

- Generated agent instructions and adapters now use the absolute launcher
  path `<home>/bin/loomsci` instead of a bare `loomsci` command.
- This prevents IDE agents from guessing `/bin/loomsci` or copying the
  launcher into the project.
- Found during a real opencode + omp handoff test; no protocol/data changes.

## v0.1.0-preview.3

- Add `loomsci agent add <handle> --tool <ide>` and `agent list`.
- New agents are created from the alice baseline with their own handle, role,
  persona, instructions, and adapters.
- This enables a real multi-IDE test with WorkBuddy / opencode / codebuddy /
  Qoder / omp.

## v0.1.0-preview.2

- Replace the Codex adapter with a WorkBuddy adapter.
- Align docs and examples with the actual IDEs in use: WorkBuddy and opencode.
- No protocol or data changes.

## v0.1.0-preview.1

First runnable local preview.

- Core host: loopback-only HTTP, Host/Origin/JSON boundary, no login.
- Profile and pack registry: `core` / `team`, disabled packs return
  `pack_disabled` and start no jobs.
- SQLite post bus and task leases; read cursors, presence, and structured
  handoff.
- Default `alice` baseline with persona, instructions, adapters, rename
  history, and persona snapshots.
- CLI: `home`, `migrate`, `features`, `serve`, `post`, `read`, `task`,
  `presence`, `handoff`, `alice`, `export`, `import`.
- Read-only status/posts/tasks pages.
- Portable export/import zip with count verification and path/symlink checks.
- Release builder, macOS/Linux installer, Windows PowerShell installer, and
  upgrade/rollback script.
- macOS installation and reinstall-preserves-data verified; Windows installer
  still needs a Windows run.

Known limitations:

- No WebSocket/SSE watch yet.
- No search endpoint yet.
- Windows installer is provided but not yet exercised on Windows.
- Single-machine only; no center, peer sync, or federation.
