# Core platform contract · v0

- Status: draft, 2026-11-14
- Supersedes: `core-contract.md` v1 (beta-era application contract)
- Applies to: the future `loomsci_core` distribution, not yet to `0.1.0-beta.28`
- Product shape: **LoomSci Core + Specific APP**
- TAA: vanguard / experiment platform; not the Core codebase

## 1. What Core is

Core is the smallest stable, local-first runtime that a LoomSci application can
depend on. It is not the product's complete feature set.

```text
LoomSci Core = workspace + storage + search + local API + app host + updater
LoomSci App  = domain model + UI + workflows + content
```

Core must remain useful when no app is installed:

- start and stop
- store generic items and blobs
- tag and search
- back up, restore, export
- install, start, stop, and update an app

Core must not require registration or a network connection.

## 2. Hard guarantees

1. **Local by default.** Bind loopback only. No account, login, cloud, or
   telemetry in Core.
2. **Core alone works.** A user can run Core without any app and still store,
   search, export, and back up artifacts.
3. **Stable app API.** Apps target `core/1`; Core keeps additive compatibility
   inside a major API version.
4. **App isolation.** Each app has its own package, data namespace, port, and
   health path. Core does not import app code.
5. **User ownership.** Data is a local workspace; export/backup is a first-class
   operation, not a paid feature.
6. **Signed distribution.** Core, apps, and content packs are verified before
   installation or use.
7. **Separate update channels.** Software updates, app updates, content updates,
   and entitlements are different operations.
8. **No forced account.** Free local use never requires registration.

## 3. Layers

```text
Core process
├─ Workspace layout
├─ SQLite + blob store
├─ Generic items / tags / search
├─ Local HTTP API + capability token
├─ App host
├─ Backup / restore / export / import
├─ Software updater
└─ Minimal web shell
        │
        ├─ Report app
        ├─ Project app
        └─ future apps
```

The minimal web shell may show Core diagnostics, app launcher, update status,
and a generic item reader. It must not become a domain application.

## 4. Workspace layout

```text
~/.loomsci/
├─ core/                 # Core code or installed runtime
├─ data/
│  ├─ core.db            # generic items, tags, apps
│  └─ blobs/             # content-addressed blobs
├─ apps/
│  └─ <slug>/
│     ├─ manifest.json
│     ├─ code/
│     └─ data/           # app namespace; preserved by default
├─ config.yaml           # local configuration; no secrets in repo
├─ logs/
├─ backups/
└─ runtime/
```

Paths are stable contract. Apps must not write outside their namespace except
through Core APIs.

## 5. Core data model

Core owns only generic primitives.

```text
items
  id            TEXT PRIMARY KEY
  app           TEXT NOT NULL
  type          TEXT NOT NULL
  title         TEXT
  body          TEXT
  metadata_json TEXT NOT NULL DEFAULT '{}'
  created_at    TEXT NOT NULL
  updated_at    TEXT NOT NULL

item_tags
  item_id       TEXT NOT NULL
  tag           TEXT NOT NULL
  source        TEXT NOT NULL DEFAULT 'ai'
  confidence    REAL
  PRIMARY KEY (item_id, tag)

blobs
  id            TEXT PRIMARY KEY
  item_id       TEXT
  filename      TEXT NOT NULL
  content_type  TEXT
  bytes         INTEGER NOT NULL
  sha256        TEXT NOT NULL
  created_at    TEXT NOT NULL

apps
  slug          TEXT PRIMARY KEY
  version       TEXT NOT NULL
  manifest_json TEXT NOT NULL
  installed_at  TEXT NOT NULL

```

App-specific tables live in the app namespace, not in Core tables.

### FTS

Core maintains FTS5 over `items.title`, `items.body`, `item_tags.tag`, and
`items.app`. Apps may add their own indexes but must not replace Core search.

## 6. HTTP API surface

Core v0 API is additive and versioned.

```text
GET    /v1/health
GET    /v1/version
GET    /v1/status

POST   /v1/items
GET    /v1/items
GET    /v1/items/<id>
PATCH  /v1/items/<id>
DELETE /v1/items/<id>

POST   /v1/items/<id>/tags
GET    /v1/tags
GET    /v1/search

POST   /v1/blobs
GET    /v1/blobs/<id>
GET    /v1/blobs/<id>/inline

GET    /v1/apps
POST   /v1/apps/install
POST   /v1/apps/<slug>/start
POST   /v1/apps/<slug>/stop
POST   /v1/apps/<slug>/update
POST   /v1/apps/<slug>/remove

GET    /v1/updates/status
POST   /v1/updates/check
POST   /v1/updates/apply

GET    /v1/backups
POST   /v1/backups
POST   /v1/backups/restore
```

Exact payloads are frozen in `docs/en/app-manifest.md` and the SDK examples.
Apps must use `/v1`; they must not import Core internals.

## 7. Local capability token

Core does **not** implement user accounts. It implements a per-install local
capability token to keep the localhost API from being used by unrelated local
pages or processes.

```text
~/.loomsci/local.token   # 0600
```

- CLI reads it automatically.
- Core web shell receives it through a same-origin session.
- Apps receive a scoped token from the app host.
- The token is not a user identity and is not sent to third parties.
- If the token is lost, Core can rotate it; app re-registration is required.

This is a security boundary, not registration.

## 8. App host responsibilities

- validate manifest and signature
- check `core_api` and `min_core`
- allocate/verify a loopback port
- create a data namespace
- start/stop/health-check the app
- pass a scoped capability token
- preserve app data on update
- remove app code without deleting user data unless manifest explicitly allows it
- surface app errors without crashing Core

## 9. Update channels

```text
core-software     signed Core binary/package
app-software      signed app package
content           signed data packs; never executable
entitlement       signed license/credit state; app-owned
```

Rules:

- content packs cannot execute code
- software and content have independent versions
- failed updates roll back to the previous working version
- offline mode keeps the last known good state
- Core never becomes a billing or entitlement server

## 10. Explicit non-goals

- user accounts, login, multi-user, teams
- chat, rooms, social feed, comments
- task assignment, execution, agent dispatch
- federation, peer sync, tunnel, discovery
- plugin marketplace
- model calls in Core
- billing, credits, subscription management
- content generation

These belong to apps or to TAA.

## 11. Compatibility and migration

- API version: `core/1`
- App manifest: `app/1`
- Schema migrations are additive; destructive changes require a new Core major.
- `0.1.0-beta.28` is the **legacy implementation**, not yet Core v0 contract.
- Migration path:
  1. inventory current `posts` / `tasks` / `facts` / `projects` tables;
  2. map current posts and attachments to `items` + `blobs`;
  3. move domain tables into Report / Project apps;
  4. keep export/backup compatibility for at least one release;
  5. remove legacy tables only after an export/restore test.

## 12. Acceptance tests for Core v0

A Core release is not distributable unless:

1. a clean machine can install Core without manual Python setup;
2. `loomsci start` works offline and serves `/v1/health`;
3. an item with Markdown and a blob survives restart, backup, restore;
4. search returns the item by body, title, tag, and app;
5. an app can be installed, started, stopped, updated, and removed;
6. app data survives app update; Core data survives app removal;
7. a signed content pack can be applied and rolled back;
8. a corrupt package is rejected with a clear error;
9. no registration is required for any local feature;
10. an app cannot read another app's namespace through Core APIs;
11. a clean machine with no Python can bootstrap Core through the pinned uv
    runtime and run the hello-world app.

## 13. Runtime contract: Python 3.12 + uv

v0 accepts Python as a runtime for AI-native technical users. The installer
provisions it; users do not install Python manually.

```text
core runtime   ~/.loomsci/runtime/python/       # uv-managed Python 3.12
core venv      ~/.loomsci/venv/                 # Core dependencies
app venv       ~/.loomsci/apps/<slug>/venv/     # app dependencies
```

Rules:

- Installer detects Python 3.12; if absent, uses `uv python install 3.12`.
- Core runs from its own venv; each app runs from its own venv.
- App Host launches `<app-venv>/python -m <package>.<entry>`.
- `requirements_file` is installed into the app venv with `uv pip install`.
- Offline installer bundles the required Python and wheels.
- Core updates must not delete or replace app venvs.
- Native single-file binaries are a later optimization, not an M0 gate.
- The installer must still work when `uv` is absent, by downloading a pinned
  `uv` binary with checksum verification.

## 14. Open questions

- exact local token transport for browser and app;
- app-to-app sharing through Core items vs app-to-app API;
- how much generic reading UI belongs in Core;
- minimum supported OS matrix for first public release.
