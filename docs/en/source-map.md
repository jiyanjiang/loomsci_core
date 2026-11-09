# Source map · S1 (reuse plan)

> Status: S1.1 started. `core/home.py` and the `migrate`/`home` CLI exist;
> no legacy modules have been copied yet.
> Goal: extract the smallest viable Core from the existing TAA codebase into
> this public repository, without a runtime dependency on the legacy tree.

## Rules

1. **One-way copy.** No symlink, no import from a private checkout, no runtime
   dependency on the old repository.
2. **Keep the `core/` package name in v1.** The public CLI is `loomsci`; a
   package rename would cause a large, risky import migration.
3. **Allowlist only.** Copy selected files; strip data, keys, local paths, and
   private docs. Run the sanitization check before every push.
4. **No pack code in Core.** Center, peer, federation, distribution, research,
   media, and executor loops stay out.
5. **Every copied module needs a test** that runs on macOS and Windows.

## Reuse matrix

| TAA asset | Decision | Notes |
|---|---|---|
| `core/agent_identity.py` | copy | `agent.owner` handle rules; add tests |
| `core/db.py` + schema | adapt | trim tables; path from `home.py`; additive migrations |
| `core/persona.py` | adapt | alice baseline; body/wardrobe off in Core |
| `core/memory.py` / memory vault | adapt | per-agent private memory; no pack assumptions |
| `core/attachments.py` | adapt | content-addressed blobs; size/type limits |
| `core/redaction.py` | copy | posts, exports, evolution and publish checks |
| `core/i18n.py` + `locales/` | copy | zh-CN/en key parity; functional strings only |
| `core/protocol.py` | copy | protocol version and capability list |
| `core/distribution.py` | adapt | signed manifest; pinned public key; no self-signed trust |
| `core/updates.py` | adapt | forced sha/bytes/channel; cross-platform; no `fcntl` at import |
| backup/export modules | adapt | non-peer parts only; JSON + Markdown + blobs |
| `static/teamai/` | subset | Core pages only; no pack navigation |

| TAA asset | Decision | Notes |
|---|---|---|
| `core/server.py` | adapt | expose a small route allowlist; do not copy 317 routes |
| `core/app_ui.py` | adapt | Core pages: home, chat, activity, tasks, memory, settings, diagnostics |
| `core/auth.py` | replace | local identity header + Host/Origin/JSON boundary |
| `core/community.py` | adapt | posts, replies, mentions, inbox; no public/friends visibility |
| `core/rooms.py` | subset | 1:1 conversation only; no multi-agent rooms |
| task module | adapt | claim/lease/status/done; single active lease |
| `core/commands.py` | defer | local CLI is enough for Core |

| TAA asset | Decision | Reason |
|---|---|---|
| `center_hub.py`, `center_sync.py` | exclude | no center node |
| `federation.py`, `peer_*`, `discovery.py`, `hub*.py`, `tunnel_client.py` | exclude | packs only |
| `group_crypto.py`, `attach_crypto.py` | defer | collab pack; not needed for local-only Core |
| `appdist.py`, `core/video`, `research.py`, `monograph.py`, `loomdoc_ui.py`, `media.py`, `weather.py` | exclude | packs or examples |
| `executor_bridge.py`, `chatwork.py`, `runtime/dispatcher.py`, `runtime/*_agent.py` | exclude | the IDE is the executor |
| share/QR/invite/join paths | exclude | collab pack |

## New modules

| Module | Purpose |
|---|---|
| `core/home.py` | resolve `LOOMSCI_HOME`; detect legacy home; migrate copy; refuse ambiguous dual homes |
| `core/profile.py` | `core` / `team` profile selection |
| `core/packs.py` | single registry for routes, background jobs, navigation |
| `core/local_auth.py` | local identity header, Host allowlist, Origin and JSON checks |
| `core/presence.py` | per-agent IDE session records |
| `core/reads.py` | per-agent read cursors |
| `core/handoff.py` | structured handoff validation and rendering |
| `cli/loomsci.py` | public CLI wrapper |
| `presets/agents/alice/` | persona, instructions, adapters |

## Target tree

```text
core/
  home.py profile.py packs.py local_auth.py
  db.py identity.py persona.py memory.py attachments.py redaction.py
  community.py tasks.py presence.py reads.py handoff.py
  i18n.py protocol.py distribution.py updates.py
cli/
  loomsci.py
presets/agents/alice/
locales/
static/teamai/        # minimal Core assets only
tests/
```

## S1 slices

| Slice | Deliverable | Acceptance |
|---|---|---|
| S1.1 | `home.py` with `LOOMSCI_HOME`, legacy detection, `migrate --dry-run` | no dual-home writes; migration count report |
| S1.2 | `profile.py` + `packs.py`; route/job/nav gating | Core `features` ≤80; disabled pack returns `pack_disabled`; no pack loops |
| S1.3 | `local_auth.py` wired into a minimal app | loopback bind; bad Host/Origin/form/oversize rejected |
| S1.4 | minimal health/version/features + one post/task path | no anonymous read of private data |
| S1.5 | macOS + Windows tests | same tests pass on both; no POSIX-only imports |

## Non-goals

- copying all routes or UI pages;
- migrating real user data in this phase;
- enabling any pack;
- building the installer;
- multi-agent rooms, E2EE, center, peer, or public feed.

## Open decisions

- Cherry-pick modules vs copy `core/` wholesale behind a gate. Recommendation:
  cherry-pick, then add the gate; a wholesale copy keeps 317 routes alive.
- Minimal dependency set: Flask + PyYAML first; cryptography only where needed.
- File-lock abstraction: POSIX `fcntl` / Windows `msvcrt`, no import-time
  platform failure.
