# N4 acceptance: scenarios, not wall-clock soak

The Core is single-machine. An idle multi-machine soak is not evidence of
quality: with no user workload it only proves that a process can stay alive.

N4 is complete when a **deterministic scenario suite** passes on a fresh home
on macOS and Windows. Elapsed time is a result, never the acceptance criterion.

## Why dual-machine soak is not required

- Core has no sync, center, federation, or multi-user state.
- macOS and Windows are two independent installs, not two replicas.
- Cross-machine behavior belongs to the future `sync` add-on; it must be tested
  when that add-on exists, with a real two-node scenario.
- A long idle run cannot exercise leases, conflicts, migration, or recovery.

A second machine is useful for **platform parity** and real-IDE evidence, not
for an idle soak.

## Scenario matrix

Every item must be executed with a fresh isolated home and a bounded workload.

### A. Install and contract

- install package, resolve home, start host
- `/v1/health`, `/v1/version`, `/v1/status`
- `features`: only implemented routes, correct nav/packs
- verify README/VERSION inside the installed tree

### B. Core lifecycle

- init owner and default agent
- post / read / cursor
- task add / claim / second claim 409 / done with evidence
- handoff post readable by the target agent
- memory add / review / search
- mention inbox / mark read
- attachment upload, post link, download
- SSE `since=0&once=1` and reconnect from a later cursor

### C. Concurrency

- N tasks, two agents racing each: exactly one `200`, one `409`
- concurrent posts from 3 agents: no lost sequence, no duplicate seq
- repeated `export` while writes continue: export remains parseable

### D. Faults and recovery

- unknown agent → 403
- malformed handle → 400
- missing/duplicate attachment → 404/409, no orphan post
- port already in use → exit 2, no second listener
- corrupt export → import fails without touching destination
- restart host: counts/integrity unchanged
- upgrade → rollback: code restored, data preserved

### E. Platform parity

Run A–D on macOS and Windows. Results must match; differences are documented,
not waived silently.

Real IDE L7 is separate evidence:

- macOS: opencode + omp
- Windows: opencode + omp (when installed)
- GUI adapters are manual evidence, not a blocker for Core

### F. Compatibility

- import an export from the previous preview
- additive migration on an existing DB
- old `loomsci.cmd`-less Windows instructions are detectable and re-generated

## Bounded workload

Recommended minimum per host:

```text
3 agents × 80 posts       = 240 posts
20 tasks, 2 racing claims = 20 × (200 + 409)
20 facts + 20 reviews
1 attachment upload/link/download
1 SSE first connect + 1 reconnect
1 export/import round-trip
1 restart
1 upgrade/rollback (when a previous package is available)
```

This is deterministic and completes in minutes. It is stronger than an hour of
idle time because it checks the invariants that can actually break.

## Exit rule

N4 is complete when:

1. A–F pass on macOS and Windows; and
2. failures are either fixed or recorded with an explicit, accepted exception;
3. docs and installed-package README/VERSION are consistent.

No feature work is allowed after N4 starts; only bug fixes and tests.
