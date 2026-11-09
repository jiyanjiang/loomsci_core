# Core contract · v1

`loomsci_core` is the small, stable head of the product. Full TAA is **Core +
add-ons**, not a larger Core. Add-ons attach through frozen contracts; they do
not force a Core rewrite.

## Core v1: what must be true

1. **One machine, one owner, one main agent** (`alice`), plus optional agents.
2. **One command start**: `loomsci init` then `loomsci serve`; loopback only,
   no login, no center, no TLS requirement.
3. **Identity**: `<agent>.<owner>`, persona, instructions, adapters, rename
   history, persona snapshots.
4. **Bus**: posts, tasks, claim/lease, handoff, read cursors, presence.
5. **Memory**: project facts and preferences that can be written, recalled,
   reviewed, exported, and reverted. No secrets; no uncontrolled drift.
6. **Assets**: project files, artifacts, attachments.
7. **UI**: read plus minimal write (post, task, memory review), not read-only.
8. **Operations**: export/import, backup, diagnostics, install, upgrade,
   rollback.
9. **Platforms**: macOS and Windows install/upgrade.
10. **IDE clients**: opencode + omp validated; WorkBuddy / codebuddy / Qoder
    adapters documented and at least one GUI client validated.
11. **Security**: loopback, Host/Origin/JSON boundary, no anonymous private
    reads, sanitization before every push.
12. **Tests**: L0–L7 from `docs/en/testing.md`; real IDE handoff; migration.

## Not Core (add-ons)

- multi-agent rooms, roles, E2EE, share/QR/invite;
- center, peer sync, federation, tunnel, discovery;
- public feed, moments, friends visibility;
- research, monograph, LoomDoc, media/video;
- APK/IPA distribution;
- LAN pairing, multi-user, plugin marketplace.

The Core keeps the **host contract** for these: pack registry, `/apps/<slug>/`
namespace, namespaced storage, and a single event/audit path.

## Frozen contracts (change only with a versioned Core release)

- `agent.owner` handles and stable agent ids;
- home layout: `core/`, `data/`, `agents/`, `packs/`, `logs/`, `runtime/`;
- SQLite IDs and additive-only migrations;
- `/v1` HTTP shapes and `loomsci` CLI names;
- post/task/lease/handoff semantics;
- export zip format and manifest version;
- pack registry (routes/jobs/nav);
- install/upgrade manifest (`preserve` / `forbid_overwrite`);
- prompt policy: hard invariants + adaptation budget.

## Node sequence

| Node | Goal | Exit gate |
|---|---|---|
| N0 · done | Contract freeze 1 (`v0.1.0-preview.6`) | install, bus, alice, agent add, export/import, UI, release, real opencode+omp handoff |
| N1 · done | Core Alpha (`v0.1.0-preview.7`) | init, post/task UI writes, memory add/review/export; Windows install spike passed |
| N2 · done | Core Beta (`v0.1.0-preview.8`) | search, watch/SSE, inbox/mentions, attachments, status recovery; restart/replay tests |
| **N3 · current** | Core RC (`v0.1.0-preview.13` prep) | upgrade signature verification and rollback tests; Windows regression + release signing key pending |
| N3 · Core RC | Windows, signed package, GitHub Release, update/rollback, migration | clean install on macOS + Windows; rollback; `latest.json` |
| N4 · Core 0.2.0 | soak and freeze | no new features; only bugfix; docs final |

Add-ons start only after N4. Suggested order: app host + first app, collab,
sync, media/dist, social.

## Today's endpoint

`v0.1.0-preview.6` remains the **foundation freeze**. N1 (`preview.7`) adds
init, facts/memory review, and minimal UI writes without changing the frozen
protocol. Next: finish N3 with Windows full regression and a real Ed25519 release key.
