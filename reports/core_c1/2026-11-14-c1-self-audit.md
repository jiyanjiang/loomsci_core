# Core C1 self-audit · 2026-11-14

- Decision: **C1 Engineering Freeze reached**
- No more Core feature work until a real app hits a blocker
- Full test suite: **203 tests OK, 3 skipped**
- Platforms: macOS + Windows

## 1. The real end point

The previous C1 checklist mixed two different things:

1. engineering readiness for app development
2. product validation by external users

The endless loop came from treating (2) as a prerequisite for (1), and from
inventing requirements not needed for Core v0.1.

The real end point is:

> **C1 Engineering Freeze**: Core exposes a stable enough v0.1 contract,
> SDK, docs, app host, backup, migration, and install/update path for another
> developer to build an app without modifying Core.

External users, 2–3 demo apps, and 30-day observation are **post-C1 validation**,
not blockers for starting app development.

## 2. Self-check

| Item | Evidence | Verdict |
|---|---|---|
| Formal package | `loomsci_core/`, `python -m loomsci_core` | PASS |
| CLI | `start` / `stop` / `status` / `doctor` | PASS |
| API | items/tags/blobs/search/backups/apps | PASS |
| App Host | install/start/stop/update/remove | PASS |
| Scoped token | app cannot cross namespace | PASS |
| Backup/restore | data-only, token regenerated | PASS |
| Migration | beta.28 -> v0, A/B apply, source unchanged | PASS |
| SDK | `loomsci_core.sdk.CoreClient` | PASS |
| Example app | `examples/hello-app` uses SDK | PASS |
| Docs | platform/API/app/maintainer, bilingual | PASS |
| OpenAPI | `docs/openapi/core-v0.json` | PASS |
| Signed package | manifest + signature + payload | PASS |
| Installer | package -> venv -> launcher -> start | PASS |
| Updater | verify -> backup -> replace -> health -> rollback | PASS |
| macOS | package/install/start/update/migration | PASS |
| Windows | package/install/start/update/migration | PASS |
| Full suite | 203 tests | PASS |

## 3. What was overreach

These are **not** C1 requirements:

- bundling Python and all wheels inside Core
- fully offline first install
- external app marketplace
- 2–3 external demo apps before starting app work
- 30-day validation before starting app work
- complete `loomsci app` CLI before app development

Python 3.12 + uv is the accepted runtime. The installer may use a preloaded or
uv-provisioned Python. A fully offline bundle is a deployment option, not a Core
engineering gate.

## 4. Accepted post-C1 work

- third-party app package signatures
- app marketplace
- fully offline Python/wheels bundle
- external demo apps and 30-day observation
- app CLI convenience commands
- more conformance tests from real app needs

These do not block Report or other apps.

## 5. Freeze rule

From this commit:

```text
Core changes only for:
  bug fixes
  security fixes
  additive API required by a real app
  documentation corrections
```

No new Core domain features. No new app-specific tables or UI. App work starts in
separate repositories.

## 6. Next

Start `LoomSci Report` as the first external app, using:

```text
SDK:    loomsci_core.sdk.CoreClient
API:    core/1
Manifest: app/1
Docs:   docs/en/core-v0/app-developer.md
```

If Report hits a missing Core capability, record it as a concrete blocker; only
then consider an additive Core change.
