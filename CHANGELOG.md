# v0.1.0-beta.20 — Advanced providers

- Add Settings → Advanced providers for Aliyun DashScope and Volcengine Ark.
- Expose base URL, model, key, and connection test.
- Provider keys remain write-only and are never returned by the API.

# v0.1.0-beta.19 — FTS5 search

- Add SQLite FTS5 indexes and triggers for posts, tasks, and facts.
- Search uses FTS5 with a LIKE fallback.
- Add 10k/50k benchmark script and tests.

# v0.1.0-beta.18 — Project templates

- Add built-in book, research, and OPC 180-day project skeletons.
- `project template list/create`; target must be empty or missing.
- Templates create new projects only; they do not copy existing project data.

# v0.1.0-beta.17 — Project evaluation rubric

- Add project evaluations with problem clarity, evidence, implementation, output, application, commercial, maintainability.
- Add `project evaluate` CLI and evaluations API/UI.
- Evaluations are human-recorded drafts/reviewed/approved; no automatic approval.

# v0.1.0-beta.16 — Project app registry

- Add project app add/list/check.
- App status: registered, running, unreachable.
- Read-only health checks; never execute project commands.
- UI displays app status and check action.

# v0.1.0-beta.15 — API/schema contract

- Add `schema_version` and `schema_migrations` ledger via SQLite user_version.
- `/v1/health` and `/v1/version` expose `api_version=core/1` and `schema_version`.
- Verify add-on manifests declare `api=core/1`.

# v0.1.0-beta.14 — Security audit

- Add Host/Origin/JSON/agent security regression tests.
- Require HTTPS for non-loopback update and package URLs.
- Re-verify downloaded bytes/SHA before install.
- Document the local-process trust boundary.

# v0.1.0-beta.13 — Update checker

- Add update status/check/download/apply APIs and CLI.
- Add Settings → Updates UI with check, download, install and restart.
- Verify bytes and SHA-256; install uses pre-upgrade backup and rollback.
- Automatic installation remains disabled; user confirms.

# v0.1.0-beta.12 — Project review gate

- New projects default to `candidate`; only `selected` become active.
- Add completeness, maturity, commercial potential, direction, notes, reviewer.
- Add `project review` CLI and review badges/scores in the project UI.
- Project review is metadata-only; no project content is copied.

# v0.1.0-beta.11 — Project dashboard

- Add project list/detail/stats/entries API.
- Add `/app/projects` list and detail views.
- Show sources, file-type counts, monthly activity, schemas, apps, recent files.
- All project views remain reference-only; no source content is copied.

# v0.1.0-beta.10 — Database schema inspector

- Add read-only SQLite and DuckDB schema inspection.
- `project inspect` stores tables, columns, row estimates, and schema hash.
- DuckDB support is a Core dependency; databases are opened read-only.
- No database files are copied.

# v0.1.0-beta.9 — Reference projects

- Add `projects`, `project_sources`, `project_entries`, `project_schemas`, `project_apps`.
- Add `project register/list/show/refresh/remove`.
- Project sources are references; files and databases are never copied.
- Add `.duckdb` detection to the scanner.

# v0.1.0-beta.8 — Project scanner

- Add read-only `loomsci project scan`.
- Detect project roots from manifests, README, docs, scripts, and databases.
- Record metadata, counts, README excerpt, DB files, and app port hints.
- Never copy project files or execute project code.

# v0.1.0-beta.7 — Login service

- Add `loomsci service install/uninstall/status`.
- macOS installs a LaunchAgent that runs `up --detach` at login.
- Windows installs a current-user Startup folder wrapper.
- No silent resident daemon; Core keeps the detached runtime state.

# v0.1.0-beta.6 — DeepSeek provider settings

- Add `GET/PUT /v1/settings/llm/deepseek` and `POST .../test`.
- Add a one-field DeepSeek key form at `/app/settings`.
- Keys are written to `config.yaml` (0600), never returned by the API, logs,
  backups, or exports.
- Summaries and the research add-on share the same provider config.
- Legacy `llm.deepseek_api_key` is read and migrated on save.

# v0.1.0-beta.5 — Runtime control

- Add `loomsci up --detach`, `loomsci status`, `loomsci down`, and `loomsci open`.
- Detached Core survives terminal close; PID/lock/state live under `runtime/`.
- One primary URL: ui-shell when running, otherwise Core `/app`.
- `loomsci status` keeps the existing API-status behavior when `--as` is used.

# v0.1.0-beta.4 — UI route hotfix

- `/app`, `/app/posts`, `/app/tasks`, `/app/memory`, `/app/inbox`, `/app/site`
  now serve the ui-shell instead of 404.
- Nav clicks update the path; browser back/forward restores the view (BUG-0003).

# v0.1.0-beta.3 — Loose list hotfix

- Fix ordered lists separated by blank lines: one `<ol>` instead of two numbered lists.
- Same fix in ui-shell, collab, and notify (BUG-0002).

# v0.1.0-beta.2 — Post summaries

- Remove the separate post title. A post is one Markdown body.
- Long posts (>800 chars) show a 300–500 character summary; short posts render in full.
- Add `post_summaries`, asynchronous DeepSeek summaries, and a local extractive fallback.
- Add `/v1/posts?view=feed` and `/v1/posts/<id>`; the feed omits long bodies.
- Fix ordered lists in collab and notify (BUG-0001).

# v0.1.0-beta.1 — Public Beta

First public beta. Local-only, single owner. See docs/en/changelog.md.

# Changelog

The canonical, detailed changelog is:

- [English](docs/en/changelog.md)
- [中文](docs/zh-CN/changelog.md)

## v0.1.0-preview.49

- Pre-upgrade asset backup with abort-on-failure and --no-backup.

## v0.1.0-preview.48

- Interactive setup, optional hidden DeepSeek key storage.

## v0.1.0-preview.47

- Setup command, IDE detection, WorkBuddy smoke baseline.

## v0.1.0-preview.46

- Windows clean-install Python discovery and `-PythonExe`.

## v0.1.0-preview.45

- G4.1: doctor diagnostics and `up` startup command; installer hints.

## v0.1.0-preview.44

- Asset boundary correction: submitted attachments are included by default;
  exclusion requires explicit reference metadata.

## v0.1.0-preview.43

- P3 target contract: sync inspect/import into an installed empty workspace;
  refuse used targets; preserve local config and non-source agents.

## v0.1.0-preview.42

- Attachment provenance, asset classification, and origin-based document/media
  backup policy.

## v0.1.0-preview.41

- Backup verify and retention; storage report logical vs physical bytes.

## v0.1.0-preview.40

- P2.6 storage report/duplicates/dedupe/prune/compact; hardlink dedupe and
  orphan cleanup dry-run by default.

## v0.1.0-preview.39

- P2.5 asset bundle create/show/restore, Markdown projection, content-addressed
  assets, references index, secret blocking/redaction.

## v0.1.0-preview.38

- P2.5 backup boundary inventory: read-only inspect, classifications, duplicate
  attachment detection, secret scan.

## v0.1.0-preview.37

- ui-shell v0.5.0 site config: name, logo, links, footer; defaults and local JSON.

## v0.1.0-preview.36

- ui-shell v0.4.0 i18n: English / Simplified Chinese, locale selector.
- Add-on server bind skips reverse DNS (macOS CI fix).

## v0.1.0-preview.35

- Add-on lifecycle: manifest package/entry/port/health, installed metadata,
  update/verify/start/stop/status, dependency checks, correct home venv.

## v0.1.0-preview.34

- Media v0.2b OCR and speech transcription, optional tools.

## v0.1.0-preview.33

- Research v0.2: optional DeepSeek Search/Chat with source gate.

## v0.1.0-preview.32

- Media v0.2a thumbnails/capabilities; OCR/transcription pending.

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
