# App manifest contract · v0

- Status: draft, 2026-11-14
- API: `app/1`
- Core API target: `core/1`
- Applies to apps distributed alongside or on top of LoomSci Core

## 1. Principle

An app is a separately versioned product that depends on Core, not a module that
rewrites Core.

```text
Core owns: workspace, items, blobs, tags, search, app lifecycle, backup, update
App owns:  domain schema, domain UI, workflows, content, optional account
```

## 2. Manifest example

```json
{
  "name": "LoomSci Report",
  "slug": "report",
  "version": "0.1.0",
  "app_api": "app/1",
  "core_api": "core/1",
  "min_core": "0.2.0",
  "max_core": "0.9.99",
  "package": "loomsci_report",
  "entry": "server",
  "port": 8791,
  "health": "/health",
  "data_namespace": "app_report",
  "permissions": [
    "items.read",
    "items.write",
    "blobs.read",
    "blobs.write",
    "tags.write",
    "search.read"
  ],
  "update_channels": ["stable", "beta"],
  "content_channels": ["daily"],
  "preserve": ["data"],
  "uninstall": "keep_data",
  "requires_registration": false
}
```

## 3. Required fields

| Field | Type | Rule |
|---|---|---|
| `name` | string | human-readable |
| `slug` | string | lowercase `[a-z0-9-]`, unique |
| `version` | semver | app version |
| `app_api` | string | `app/1` |
| `core_api` | string | `core/1` |
| `min_core` | semver | minimum compatible Core |
| `max_core` | semver | optional upper bound |
| `package` | string | importable directory name |
| `entry` | string | module name under package |
| `port` | int | loopback port; `0` means Core allocates |
| `health` | string | HTTP path |
| `data_namespace` | string | isolated storage namespace |
| `permissions` | array | requested Core capabilities |
| `update_channels` | array | software update channels |
| `content_channels` | array | content pack channels |
| `preserve` | array | `data` / `config` / `none` |
| `uninstall` | string | `keep_data` / `remove_data` |
| `requires_registration` | bool | app-level only; Core never requires it |

## 4. Optional fields

```text
description
homepage
license
icon
min_os
screenshots
capabilities
default_profile
compatibility
```

## 5. Permissions

Core enforces a small, explicit permission set:

| Permission | Meaning |
|---|---|
| `items.read` | read items in the app's namespace |
| `items.write` | create/update/delete items in the app's namespace |
| `items.cross_read` | read items from other apps (explicit approval) |
| `blobs.read` | read blobs attached to app items |
| `blobs.write` | attach blobs to app items |
| `tags.read` | read tags |
| `tags.write` | add/remove tags |
| `search.read` | use Core FTS |
| `apps.list` | list installed apps |
| `content.read` | install signed content packs |
| `update.self` | update this app |

Default: no permission. Apps declare only what they need.

## 6. Lifecycle

```text
install
  validate manifest
  validate signature/checksum
  check core_api + min_core/max_core
  create data namespace
  copy code
  register in Core apps table

start
  allocate/verify port
  launch entry with scoped token
  wait for health
  mark running

stop
  graceful shutdown
  mark stopped; preserve data

update
  stop if running
  backup current code/data
  verify new package
  replace code, preserve data
  start and health-check
  rollback on failure

remove
  stop
  remove code
  keep data by default
  optional explicit remove_data only with confirmation
```

## 7. Bootstrap installer

The Report app is the primary entry point for most users.

```text
Report installer
  ├─ detect Core
  │   ├─ binary on PATH
  │   ├─ workspace metadata
  │   └─ /v1/health
  ├─ if missing:
  │   download signed Core package
  │   verify sha256 and signature
  │   install Core
  ├─ verify core_api compatibility
  ├─ install Report app
  └─ start Core + Report; open local UI
```

Rules:

- install Core once; do not create duplicate workspaces
- never silently overwrite an existing Core
- uninstall Report leaves Core and user data intact
- offline installer bundle is supported
- no registration during install

## 8. Content packs

Content is separate from software.

```json
{
  "kind": "content",
  "app": "report",
  "channel": "daily",
  "version": "2026-11-14",
  "published_at": "2026-11-14T00:00:00Z",
  "items": [
    {
      "id": "daily-2026-11-14-1",
      "title": "…",
      "url": "…",
      "summary": "…",
      "tags": ["…"]
    }
  ],
  "sha256": "…",
  "signature": "…",
  "license": "free"
}
```

Rules:

- content cannot contain executable code
- content is cached locally
- failed content updates keep the last good version
- paid content requires app entitlement, not Core registration
- content update must not block Core startup

## 9. Compatibility

- `app_api` and `core_api` are independent.
- `min_core` / `max_core` gate installation.
- Core must expose a diagnostic when an app is incompatible.
- Core API changes are additive within `core/1`.
- App database migrations are app-owned and additive.

## 10. Example apps

### Report

```text
app/report
owns: reports, sources, evidence, daily content, reading UI
uses: items, blobs, tags, search
```

### Project

```text
app/project
owns: projects, tasks, decisions, agent roles, handoffs, reviews
uses: items, blobs, tags, search
```

Project does not execute agents. It records project state; AI IDEs execute.

## 11. Acceptance tests

1. Report installs on a clean machine and installs Core if missing.
2. A user who never registers can use all local Report features.
3. App update preserves app data and Core data.
4. App removal preserves data by default.
5. A signed content pack applies offline and rolls back.
6. An app without permission cannot read another namespace.
7. A Core version outside `min_core`/`max_core` is refused with a clear error.
8. An invalid signature is refused before code is copied.

## 12. Non-goals

- third-party app marketplace in v0
- app-to-app arbitrary RPC
- app-level billing in Core
- app-owned user identities
- content packs that execute code
- apps that require admin privileges
