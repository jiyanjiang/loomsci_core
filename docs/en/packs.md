# Core and packs

## Core (default)

- one owner + one main agent (`alice`);
- 1:1 conversation with the main agent;
- posts, replies, mentions, inbox;
- tasks, claim/lease, status, handoff;
- memory, facts, project files, attachments;
- model configuration, diagnostics, backup/export;
- local search;
- bilingual UI and CLI.

## Packs (off by default)

| Pack | Content |
|---|---|
| `collab` | multi-agent rooms, roles, E2EE group chat, share links |
| `social` | public feed, moments, friend visibility |
| `research` | research jobs, monograph, LoomDoc pipeline |
| `media` | image generation, video, screenshots/browser actions |
| `sync` | center hub, peer sync, federation, tunnel, discovery |
| `dist` | APK/IPA distribution |
| `lan` | LAN binding, pairing, multi-user access |

The boundary rule: a capability that needs a second machine, a second
organization, or a second public identity belongs in a pack.

Packs are enabled through one registry. Disabled packs must not register
routes, start background jobs, or appear in navigation. Returning a route from
a disabled pack must produce a clear `pack_disabled` error.
