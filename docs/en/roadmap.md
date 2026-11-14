# Roadmap · Core + Apps

> No dates are promised. A phase is complete only when its acceptance check
> passes. `0.1.0-beta.28` is the legacy implementation; this roadmap describes
> the Core + Apps product line, not a continuation of the current feature set.

## Positioning

```text
LoomSci Core = minimal, stable, local-first runtime for AI-native technical users
LoomSci App  = vertical product on top of Core
TAA          = vanguard experiment platform, not the Core codebase
```

- Primary users: AI-native researchers, independent developers, AI makers, small
  technical teams.
- Not a mass-market notes app, not a general AI workspace, not a TAA clone.
- Python 3.12 is an accepted runtime; installers provision it with `uv` when
  needed. Native binaries are not an M0 blocker.
- No mandatory registration. Paid/cloud features are app-level.

## M0 · Architecture freeze

**Goal:** make Core and App contracts executable, not just declared.

Deliverables:

- Process contract: app launch, token transport, health check, exit codes,
  stdout/stderr, crash/restart.
- Runtime contract: Python 3.12 + uv-managed runtime + venv layout + offline
  bootstrap.
- Signing and trust: ed25519 key hierarchy, public-key distribution, rotation,
  revocation, offline verification.
- Data layering: Core `items` vs app-owned tables; Report/Project mapping.
- Backup/restore semantics: scope, format, overwrite/merge, version mismatch,
  failure behavior.
- Migration plan: beta.28 tables → Core/app tables, field mapping, rollback.
- A hello-world app and a minimal app-host prototype.

Acceptance:

```text
install → start → call Core API → stop → update → remove
```

passes on clean macOS, Windows, and Linux machines, with no manual Python setup.

Exit / kill:

- Any P0 contract question unresolved → stop; do not enter M1.
- Hello-world app cannot complete the lifecycle on two platforms → stop.

## M1 · Core v0

**Goal:** a minimal Core that a real app can depend on.

Deliverables:

- Core package and CLI: `start`, `stop`, `status`, `doctor`.
- `/v1/items`, `/v1/blobs`, `/v1/tags`, `/v1/search`.
- App host: install/start/stop/update/remove.
- Backup/restore.
- Signed package verification.
- Local capability token.
- Minimal web shell for diagnostics and app launch.

Acceptance:

- Core contract §12: 10/10.
- Additional Core tests: at least 8/10 (startup time, memory, 10k search,
  concurrent writes, corrupt DB, token permissions, app timeout, app crash,
  backup format, truncated restore).
- A non-Report example app completes the full lifecycle.
- Example app remains healthy for 24 hours.

Exit / kill:

- App host cannot keep the example app running for 24 hours → do not enter M2.

## M2 · Report v0 + installer

**Goal:** the first real product and the primary distribution entry.

Deliverables:

- Report app: reports, sources, evidence, reading UI, daily content.
- Report installer: detect Core; install Core via uv if missing; install Report;
  start; open local UI.
- Content pack apply/rollback for the `daily` channel.
- beta.28 data migration tool if M0 approves it.

Acceptance:

- App contract §11: 8/8.
- Distribution tests: at least 10/13.
- Five technical users install on clean machines in under 10 minutes.
- A user never registers and can use all local Report features.
- Report uninstall preserves Core and user data.

Exit / kill:

- Clean macOS or Windows install fails → do not enter M3.
- Installer creates duplicate workspaces → stop and fix.

## M3 · Project v0 + update channels

**Goal:** the second app and a stable update model.

Deliverables:

- Project app: projects, tasks, decisions, evidence, agent roles, handoffs,
  reviews.
- Core software update.
- App software update.
- Content update.
- Entitlement update at app level.

Acceptance:

- Four update channels operate independently.
- Core update failure rolls back.
- App update failure rolls back.
- Content update failure rolls back.
- Offline mode degrades gracefully for all channels.

Exit / kill:

- Any update channel can cause data loss or prevent Core startup → do not enter M4.

## M4 · Technical beta

**Goal:** validate real use with the target niche.

Deliverables:

- macOS and Windows installers.
- Documentation: install, user, app developer.
- Release checklist and checksums/signatures.
- Migration and uninstall guidance.

Acceptance:

- Distribution model §7: 8/8.
- All contract acceptance tests pass.
- 20 technical users complete install and first meaningful task.
- 30-day retention and paid-interest data collected.
- At least 3 users willing to pay for Report/Project capabilities.

Exit / kill:

- Install or retention fails → stop, merge into TAA, or return to a CLI-only
  project-asset tool.
- Do not add new apps before this gate.

## Critical path

```text
Process contract
→ Core items/API
→ App host
→ Report installer
→ Report app
→ Project app
→ update/content channels
→ technical beta
```

## Explicitly not in this roadmap

- user accounts, login, multi-user, teams
- chat, rooms, social feed
- task dispatch, agent execution
- federation, peer sync, tunnel
- plugin marketplace
- billing inside Core
- native binary as an M0 requirement
- mass-market onboarding

## Next action

Write the Process Contract and the Python/uv runtime contract, then validate them
with a hello-world app on macOS, Windows, and Linux.

No product code starts before M0 passes.
