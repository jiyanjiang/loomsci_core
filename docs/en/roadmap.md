# Roadmap

> No dates are promised. A phase is complete only when its acceptance check
> passes on macOS and Windows.

## G0 · Public seed (current)

- bilingual README and docs;
- architecture, CLI, packs, roadmap, changelog;
- license, security, contributing, conduct;
- public-tree check;
- no runnable host.

## G1 · Core host

- `~/.loomsci` home and migration from the legacy home;
- single loopback port (8787);
- profile/pack gating;
- local identity and request-origin boundary;
- default one agent (`alice`).

## G2 · Collaboration bus

- posts, replies, mentions, inbox;
- tasks, claim/lease, status, handoff;
- presence and read cursors;
- `loomsci` CLI.

## G3 · Portable assets

- export/import with count verification;
- project manifest;
- diagnostics;
- first cross-platform installer.

## G4 · Preview release

- macOS and Windows installers;
- signed artifacts and checksums;
- public source snapshot;
- community issue/discussion workflow.

## Later

- optional packs (collab, research, media, sync, dist, lan);
- optional public identity mapping;
- app host under `/apps/<slug>/`.
