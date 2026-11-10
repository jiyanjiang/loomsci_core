# Changelog

All notable changes are documented here. The project follows a
`MAJOR.MINOR.PATCH` product version; preview builds may use a `-preview`
suffix.

## v0.1.0-preview.17

- Fix Windows agent instructions: when a `loomsci.cmd` launcher exists (or the
  host is Windows), generated instructions use the `.cmd` path instead of the
  extensionless Unix path. This was observed in real Windows omp L7.
- No protocol or data changes.

## v0.1.0-preview.16

- Documentation/package alignment only: README quickstart now uses the actual
  installer and `loomsci init`; status reflects the 26 Core routes, macOS L7,
  Windows L0-L6, and unsigned/no-Release scope.
- N3 is marked done with signing/GitHub Release explicitly out of scope; N4
  (soak/freeze) is the current node.
- No code behavior changes.

## v0.1.0-preview.15

- Real macOS dogfood: opencode audited Core and found three usability issues;
  omp reviewed the fixes and passed all three.
- `--as/--url/--home` are accepted after the subcommand, matching docs/UI
  examples (`loomsci post --as ... --body ...`).
- `loomsci read` non-JSON output now includes the post body.
- UI task claim/done failures are visible via `?error=...`; tasks claimed by
  another agent show an explicit message instead of silently doing nothing.

## v0.1.0-preview.14

- macOS convergence: the Core route registry now advertises only routes that
  are actually served (26); navigation is `home/posts/tasks/memory/inbox`.
- Add task claim/done actions to `/app/tasks`, so the local UI can complete the
  basic task lifecycle.
- Reject unknown/already-linked attachments before inserting a post, avoiding
  an orphan post when attachment validation fails.
- No signing, GitHub Release, or distribution ceremony in this candidate.

## v0.1.0-preview.13

- Fix the packaged README still naming preview.11: the README current-version
  text now matches the package build.
- Make `agent prune` safe by default: it lists DB-only rows and only deletes
  with `--yes` (or `--dry-run` to list explicitly).
- Package verification now checks the README version before release.

## v0.1.0-preview.12

- L7 real-IDE test on macOS: opencode v2.0.20 and omp 18.18.3 both discovered
  the absolute CLI, posted, and read back; no launcher/project pollution.
- Fix a real L7 failure: a project `math.py` shadowed stdlib when the CLI ran
  from the project cwd. Launchers now set `PYTHONSAFEPATH=1`; `upgrade.py`
  refreshes an existing launcher.
- Add `agent list --all` (show DB-only rows) and `agent prune` (remove DB rows
  without an agent home) to reconcile the roster observation.
- Windows L0-L6 passed; Windows dual-IDE L7 remains waived by the user.

## v0.1.0-preview.11

- Fix Windows export to another drive: build the temporary zip in the
  destination directory instead of `%TEMP%` so `os.replace` stays on one
  filesystem (WinError 17).
- Add a `serve` port preflight; on Windows use `SO_EXCLUSIVEADDRUSE`. A busy
  port now exits with a clear error instead of a second hidden instance.
- Enforce the local agent roster for authenticated API requests; unknown
  handles return `403 unknown_agent` (matches the CLI contract).
- Update README current-version text.
- Confirms the Windows report items: export cross-drive, duplicate port bind,
  and unknown-agent posting.

## v0.1.0-preview.10

- Ship `cryptography` so Ed25519 upgrade signature verification works after a
  normal install; CI now exercises the signed-upgrade path.
- This build is still unsigned; Windows full regression remains open.

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
