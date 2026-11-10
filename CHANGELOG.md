# Changelog

The canonical, detailed changelog is:

- [English](docs/en/changelog.md)
- [中文](docs/zh-CN/changelog.md)

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
