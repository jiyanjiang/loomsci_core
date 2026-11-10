# Add-on plan

Core is the long-lived kernel. UI and capabilities are add-ons. This document
is a contract plan, not an implementation promise. Add-ons are built in the
listed order; each must prove the Core contract is sufficient before the next
one is started.

## Principles

1. Core never imports add-on code.
2. Add-ons use `/v1` or a documented public Core API; they do not import
   `core.storage` internals.
3. Every add-on has its own route namespace, storage namespace, migrations,
   version, tests, and uninstall path.
4. Additive-only changes: no Core table rewrite, no breaking `/v1` shape.
5. UI is a shell; it renders data and calls APIs, but owns no business truth.
6. A missing add-on must not make Core unusable.
7. Build the second real add-on before over-generalizing the pack framework.

## Catalog and order

| # | Add-on | Purpose | Depends on | Risk |
|---|---|---|---|---|
| 0 | `ui-shell` | Markdown, themes, navigation, better empty/error states | Core API | low |
| 1 | `app-host` | install/uninstall add-ons, `/apps/<slug>/`, manifest/permissions, profile selection | Core minimal host (preview.20); full app-host deferred | medium |
| 2 | `collab` | rooms, threads, roles, presence, richer handoff | Core posts/tasks | medium — preview.21 rooms/threads done |
| 3 | `notify` | digest, unread summary, desktop/WezTerm/email adapters | Core inbox, collab optional | low — preview.22 digest done |
| 4 | `media` | image/audio/video library, thumbnails, OCR/transcription | Core attachments, app-host | medium — v0.2b OCR/transcription done (optional tools) |
| 5 | `research` | sources, citations, notes, monograph/report workflow | Core memory, media | high — v0.2 optional DeepSeek retrieve/ask done |
| 6 | `sync` | multi-machine identity, backup/restore, center/peer sync | Core export/import, app-host | high |
| 7 | `social` | public profile, feed, friend/invite, share links | collab + sync | high |

`app-host` may be folded into Core if a minimal install/uninstall registry is
needed for the first add-on. Do not implement it speculatively; extract it when
`ui-shell` needs to be installed as a separate package.

## Default profiles

| Profile | Add-ons | Scenario |
|---|---|---|
| `minimal` | none | Core only; CLI-first |
| `personal` | `ui-shell`, `notify` | one owner, one machine |
| `maker` | `ui-shell`, `media`, `research` | creator/researcher |
| `team` | `ui-shell`, `collab`, `notify`, `sync` | small trusted team |
| `full` | all stable add-ons | power user; explicit opt-in |

Installation must allow:

```bash
loomsci addon list
loomsci addon install ui-shell
loomsci addon install --profile personal
loomsci addon remove ui-shell
```

Profiles are recommendations, not forced bundles.

## Manifest

```json
{
  "name": "ui-shell",
  "version": "0.1.0",
  "api": "core/1",
  "requires": ["core/1"],
  "routes": ["/apps/ui/*"],
  "storage": "addon.ui",
  "migrations": ["001_init.sql"],
  "jobs": [],
  "nav": [{"label": "UI", "href": "/apps/ui/"}],
  "preserve": ["data/addons/ui/"]
}
```

Rules:

- `api` is the Core contract version, not the add-on version.
- `routes` must be under `/apps/<name>/` except a small approved Core UI slot.
- `storage` maps to an isolated directory and/or table prefix.
- `migrations` are additive and idempotent; no cross-add-on tables.
- `jobs` are disabled unless the profile enables the add-on.
- `preserve` survives upgrade/uninstall according to policy.

## Implementation sequence

### Phase 0: N4 freeze

Finish the scenario suite in `docs/en/n4-acceptance.md`; freeze Core contract
v1. No add-on code before this.

### Phase 1: `ui-shell`

- Markdown rendering, code blocks, safe links
- better posts/tasks/memory/inbox/attachments views
- no Core API changes; no new tables
- proves the shell boundary

### Phase 2: `app-host` only if needed

- install/list/remove add-ons
- profile selection
- manifest validation and version compatibility
- no marketplace/network yet

### Phase 3: `collab`, then `notify`

- rooms/threads over Core posts/tasks
- notifications from Core inbox/mentions
- no E2EE, no center, no remote sync yet

### Phase 4: `media`, then `research`

- media processing depends on attachments
- research depends on memory + sources + media
- each add-on has its own storage and migrations

### Phase 5: `sync`, then `social`

- sync is the highest-risk add-on; needs identity, conflict handling, backup,
  upgrade compatibility, and a real two-node test
- social only after sync/collab are stable
- E2EE, if ever, is a sync/collab extension, never a Core requirement

## What not to do

- Do not add a center, login, TLS, or multi-user to Core.
- Do not make the UI import Core internals.
- Do not put version data in the shell.
- Do not create one schema shared by all add-ons.
- Do not build a plugin marketplace before two real add-ons exist.
- Do not make `sync` part of the Core critical path.

## Solo-maintenance rules

- One feature per phase; finish tests and docs before the next.
- One source of truth per concept.
- Every add-on can be removed without losing Core data.
- Every upgrade has a rollback and an old-export import test.
- Release only when the package, docs, and checksums agree.
- Prefer deleting a feature to supporting two implementations.

## Image policy

- Core stores originals; hard attachment limit is 16MB.
- No silent compression in Core or ui-shell; screenshots/code images keep
  fidelity.
- ui-shell warns above 8MB (planned) and accepts up to the Core limit.
- `media` v0.2 may generate previews/thumbnails (target <=1MB) and optional
  transcodes, but must keep the original unless the user explicitly deletes it.
- Sharing/distribution compression is a media policy, not a Core contract.
