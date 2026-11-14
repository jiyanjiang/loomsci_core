# Distribution model · Core + Apps

- Status: draft, 2026-11-14
- Related: `core-contract.md`, `app-manifest.md`

## 1. Repositories

```text
loomsci_core      public   Core runtime, CLI, app host, SDK
loomsci_report    public   Report app + installer
loomsci_project   later    Project app
```

Rules:

- Core and apps are versioned independently.
- Apps depend on `core/1`; they do not copy Core internals.
- Core release cadence is slow; app release cadence can be faster.
- Shared behavior is tested by contract tests, not by shared source files.
- Core repo owns the app manifest schema and example app.

## 2. Entry points

Most users should enter through Report:

```text
LoomSci Report installer
→ detect/install Core
→ install Report app
→ start Core + Report
```

Advanced users can install Core alone:

```text
loomsci-core installer
→ Core only
→ optional app install later
```

No registration is required at either entry.

## 3. Package verification

Every downloadable artifact has:

```text
name
version
platform
arch
sha256
signature
min_core
max_core
published_at
```

Installers must verify before extraction. A failed verification must not leave a
half-installed Core or app.

## 4. Offline and partial connectivity

- Core works fully offline.
- Report's local reading works offline.
- Free content packs can be cached.
- Paid/cloud features may require connectivity, but must fail gracefully.
- Core must not block startup on a network call.

## 5. Update separation

```text
Core software update   → Core updater
App software update    → app host
Content update         → app/content channel
Entitlement update     → app/account layer
```

A content update must never install executable code.  
An app update must never rewrite Core.

## 6. Paid apps and content

- Core is free and local.
- Report/Project may have free local features and paid cloud/content features.
- Entitlements are app-owned and signed.
- Core does not handle billing, credits, or user identity.
- A user who never registers keeps full local Core + app functionality.
- Paid content may require an account, but must not disable local data access.

## 7. Release gates

A public release requires:

1. clean-machine install test;
2. Core offline start;
3. app install/start/stop/update/remove;
4. backup/restore after app update;
5. content pack apply/rollback;
6. signature failure test;
7. no duplicate workspace on Report bootstrap;
8. uninstall preserving data.
