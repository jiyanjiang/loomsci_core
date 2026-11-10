# Changelog

The canonical, detailed changelog is:

- [English](docs/en/changelog.md)
- [中文](docs/zh-CN/changelog.md)

## v0.1.0-preview.31

- Research v0.1 add-on: deterministic workspaces, sources, facts, gate, publish.

## v0.1.0-preview.30

- Fix 413/512KB screenshot upload limits; real clipboard paste verified.

## v0.1.0-preview.29

- Fix POSIX TIME_WAIT port preflight false positive.

## v0.1.0-preview.28

- ui-shell paste diagnostics: no-store assets, document-level paste, clipboard button.

## v0.1.0-preview.27

- ui-shell clipboard fallback/files/drop and diagnostic.

## v0.1.0-preview.26

- ui-shell clipboard image paste; attached on submit.

## v0.1.0-preview.25

- Media v0.1 add-on: library, classification, preview/playback.

## v0.1.0-preview.24

- ui-shell 0.3.0 baseline theme: tokens, light/dark, contrast, focus, responsive.

## v0.1.0-preview.23

- ui-shell 0.2.0: functional Markdown/LaTeX/media/search/upload target.

## v0.1.0-preview.22

- Notify add-on: unread summary, digest, mark-all-read.

## v0.1.0-preview.21

- Collab add-on: rooms/threads over Core posts.

## v0.1.0-preview.20

- Minimal add-on host: list/install/remove/profile; ui-shell via personal profile.

## v0.1.0-preview.19

- First add-on `ui-shell`: Markdown UI, proxy to Core; Core unchanged.

## v0.1.0-preview.18

- Corrupt export import fails cleanly without creating destination.

## v0.1.0-preview.17

- Windows instruction launcher uses `.cmd`; observed in real Windows omp L7.

## v0.1.0-preview.16

- Docs/package alignment: README quickstart/status, route count, N3 done scope.

## v0.1.0-preview.15

- Real macOS dogfood fixes: global flags after subcommands, read body output,
  visible UI task errors.

## v0.1.0-preview.14

- Route registry matches served routes; task UI claim/done; attachment precheck.

## v0.1.0-preview.13

- Fix packaged README version; make `agent prune` dry-run by default and require
  `--yes` to delete.

## v0.1.0-preview.12

- macOS L7 opencode+omp pass; launcher safe-path fix; agent list --all/prune.

## v0.1.0-preview.11

- Fix cross-drive export temp path, add serve port preflight, and enforce the
  local agent roster.

## v0.1.0-preview.10

- Ship `cryptography` for signed upgrade verification; CI covers it. Still unsigned.

## v0.1.0-preview.9

- Upgrade signature verification and apply/rollback safety tests; Windows and
  real signing key still pending.

## v0.1.0-preview.8

- Local search, mention inbox, SSE watch, attachments, and status/integrity.

## v0.1.0-preview.7

- One-command `loomsci init`; project facts/memory with review; minimal UI
  writes for posts/tasks; facts export/import.
- Windows install spike passed; Windows multi-IDE remains untested (opencode
  only on the test machine).

## v0.1.0-preview.6

- Local data permissions: DB 0600, home 0700, persona 0600.

## v0.1.0-preview.5

- Project-first, discovery-first prompts; testing plan and iteration loop.

## v0.1.0-preview.4

- Generated instructions use the absolute `<home>/bin/loomsci` launcher path.

## v0.1.0-preview.3

- Add multi-agent registration (`agent add/list`) for real multi-IDE tests.

## v0.1.0-preview.2

- WorkBuddy adapter replaces Codex; docs target WorkBuddy and opencode.

## v0.1.0-preview.1

First runnable local preview: Core host, post/task bus, alice baseline, CLI,
read-only UI, export/import, and release/install/upgrade scripts.
