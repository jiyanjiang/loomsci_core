# Core cutoff plan · v0

- Date: 2026-11-14
- Purpose: define when Core is stable enough that app development can continue
  independently, including by other developers
- Rule: do not let external developers build against M1 prototype code

## 1. The cutoff

```text
C0  M1 end-to-end prototype        internal only, not a platform
C1  Core v0.1 App Platform Preview  first external app developers
C2  Core v1.0 Stable                public app platform
C3  Core maintenance                fixes/security only
```

The **real cutoff is C1 Engineering Freeze**. At C1, `core/1` and `app/1` are
frozen and apps can be developed in separate repositories. Core retires feature
work and only accepts bug/security/additive changes.

**Revision 2026-11-14:** external demo apps and the 30-day observation window
are post-C1 product validation, not engineering requirements. Python 3.12 + uv
is the accepted runtime; bundling Python/wheels is a deployment option, not C1.

## 2. C0 · M1 end-to-end

Current state:

```text
items / tags / blobs / search
App Host + scoped app tokens
backup / restore
migration apply
CLI start/stop/status
migrated workspace loads
macOS PASS, Windows PASS
```

C0 is a prototype. It is not an SDK and must not be handed to external app
developers.

C0 exit gate:

- M1 acceptance passes on macOS + Windows
- one demo app runs with scoped token
- backup/restore and migration apply pass
- all `prototype/` code is marked non-product

## 3. C1 · Core v0.1 App Platform Preview

This is the cutoff for **starting other apps**.

### Required deliverables

1. **Core runtime**
   - `core` package/entry point, not `prototype/core_v0`
   - CLI: `start`, `stop`, `status`, `doctor`, `app`, `backup`
   - local token and scoped app token
2. **Frozen contracts**
   - `core/1` API
   - `app/1` manifest
   - workspace layout
   - items/tags/blobs schema
   - backup format
   - app lifecycle
3. **App SDK**
   - Python SDK (minimum)
   - app template
   - example app in a separate directory/repo
   - manifest validator
4. **API documentation**
   - OpenAPI or equivalent endpoint reference
   - error codes
   - permission table
5. **Distribution**
   - signed Core package
   - signed app package layout
   - updater with backup/rollback
   - clean install on macOS + Windows
6. **Conformance**
   - contract tests for Core
   - SDK tests
   - example app lifecycle on macOS + Windows
7. **Handoff docs**
   - `app-developer.md`
   - `core-maintainer.md`
   - release/version policy
   - security policy

### C1 acceptance

```text
1. clean macOS install + start
2. clean Windows install + start
3. items/blobs/search via SDK
4. example app install/start/stop/update/remove
5. scoped app cannot read another app
6. backup/restore
7. signed package verify + rollback
8. migrated beta.28 workspace opens
The engineering evidence is recorded in
`reports/core_c1/2026-11-14-c1-self-audit.md`.

Post-C1 validation (not an engineering blocker):

- 2–3 external developers build an app without modifying Core
- 30 days without a breaking `core/1` change

## 4. C2 · Core v1.0 Stable

C2 is after real app development, not before.

Required evidence:

- at least 3 apps built outside Core by at least 2 owners
- no Core source changes required for those apps
- `core/1` unchanged or only additive for 90 days
- backup/restore/migration exercised on real workspaces
- update/rollback exercised on both platforms
- public app template and SDK docs validated by an external developer
- security review of local token, app isolation, and package verification

C2 can change:

- docs, packaging, performance, bug fixes
- additive API
- app SDK ergonomics

C2 cannot change without a new major:

- `core/1` breaking shapes
- item/blob/tag identity
- backup format
- app manifest meaning
- app lifecycle semantics

## 5. C3 · Maintenance mode

After C2:

- Core accepts bug/security fixes and additive API only
- new domain features go into apps
- breaking changes require `core/2` and a migration plan
- new apps do not wait for Core releases

## 6. What app developers can build after C1

```text
LoomSci Report
LoomSci Monograph
LoomSci Project
science communication
fiction / long-form writing
policy brief
domain-specific readers
```

They own:

```text
domain schema
UI
workflows
content
optional account/payment
```

They do not own:

```text
Core DB
Core token
app host
backup/update
```

## 7. What Core must stop doing at C1

- no new domain features in Core
- no Report/Project-specific tables
- no app-specific UI in Core
- no new app types added to Core just to satisfy one app
- no silent API changes

New app requirements first go through the app layer. Only generic, reusable
capabilities enter Core, and only in a new additive release.

## 8. Handoff package

Before inviting other developers:

```text
loomsci_core/
├─ core/
├─ sdk/python/
├─ examples/hello-app/
├─ docs/
│  ├─ app-developer.md
│  ├─ core-maintainer.md
│  ├─ core-contract.md
│  ├─ app-manifest.md
│  └─ release.md
├─ tests/
│  ├─ contract/
│  └─ conformance/
└─ scripts/
   ├─ app-test
   └─ package
```

App developers should be able to:

```bash
loomsci app init my-app
loomsci app test ./my-app
loomsci app install ./my-app
```

without reading Core internals.

## 9. Current gap to C1

```text
[ ] move prototype into product core
[ ] SDK + app template
[ ] OpenAPI/API reference
[ ] signed Core/app package integration
[ ] updater + rollback
[ ] clean installers macOS/Windows
[ ] conformance suite
[ ] app-developer handoff docs
[ ] 2–3 external demo apps
[ ] 30-day no-breaking-change window
```

## 10. Decision

**Cutoff = C1 Core v0.1 App Platform Preview.**

At that point:

- Core stops feature development
- apps move to separate repositories
- other developers can build against `core/1` + `app/1`
- Core only fixes, hardens, and extends additively
- C2/v1.0 is earned by external app use, not declared in advance
