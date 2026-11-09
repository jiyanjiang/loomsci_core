# Changelog

All notable changes are documented here. The project follows a
`MAJOR.MINOR.PATCH` product version; preview builds may use a `-preview`
suffix.

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
