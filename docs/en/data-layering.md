# Data layering and backup semantics · v0

- Status: M0 draft, 2026-11-14
- Applies to: LoomSci Core + Apps
- Related: `core-contract.md`, `app-manifest.md`
- Decision: Core `items` are canonical for readable artifacts; App databases are
  canonical for domain state and relations.

## 1. Layer model

```text
Core
├─ core.db        canonical artifact content, tags, app registry
├─ blobs/         canonical blobs
└─ FTS            derived search index

App
├─ apps/<slug>/data/app.db   canonical domain state/relations
└─ references to Core item ids
```

No app writes to another app's database. Cross-app readable artifacts go through
Core `items`.

## 2. What goes where

| Data | Canonical owner | Example |
|---|---|---|
| Article/report body, title, summary | Core `items` | a report's Markdown |
| Tags | Core `item_tags` | `physics`, `pisa` |
| Attachments/images/PDF | Core `blobs` | figure, source PDF |
| Search index | Core (derived) | FTS5 |
| Report source registry | Report app DB | DOI/URL/excerpt |
| Reading progress/highlights | Report app DB | per-user local state |
| Project/task/decision relations | Project app DB | task belongs to project |
| Agent roles/handoffs | Project app DB | local project state |
| Render jobs/templates | Report app DB | PDF/EPUB pipeline |

Rule:

```text
Readable artifact → Core item
Workflow/relation/state → App DB
```

An app may create a Core item projection for a searchable entity. It must not
duplicate the body; store the item id in the app DB.

## 3. Item type convention

```text
<app>.<type>
```

Examples:

```text
report.report
report.source_note
project.project
project.decision
monograph.chapter
```

`metadata_json` is app-defined. v0 requires no global schema; apps declare
`metadata_schema_version` in their manifest.

## 4. Report mapping

```text
Report item (Core)
  type: report.report
  title: report title
  body: canonical Markdown
  metadata_json: { "style_code": "...", "audience": "...", "status": "..." }
  tags: [...]
  blobs: figures, PDFs, source snapshots

Report DB
  sources: DOI/URL/title/license/excerpt/hash
  evidence: claim -> source -> level
  render_jobs: md/pdf/epub paths/status
  reading_state: read/highlight/note
```

Deleting a report item deletes the Core artifact and blobs; the Report DB rows
must be deleted by the app in the same operation, or marked orphaned.

## 5. Project mapping

```text
Project item (Core)
  type: project.project
  title: project name
  body: short overview
  metadata_json: { "status": "...", "review_status": "..." }

Project DB
  projects: project records and settings
  tasks: task rows referencing project items
  decisions: decision rows
  evidence_links: item/source links
  agent_roles: roles and handoffs
```

Tasks/decisions are not required to be Core items in v0; if they need cross-app
search, the app creates projection items with type `project.task` etc.

## 6. Cross-app access

v0 removes `items.cross_read`.

- An app can read only its own namespace.
- Cross-app sharing requires an explicit future export/import API.
- No app-to-app RPC in v0.
- Core may expose a read-only projection to the minimal UI, but not raw app DBs.

## 7. Backup scope

Default backup is **data-only full workspace**:

```text
manifest.json
data/core.db
data/blobs/
apps/<slug>/data/
apps/installed.json
```

Excluded by default:

```text
local.token
logs/
runtime/
venvs/
app code
caches
temporary files
```

Optional `--with-code` adds app code for offline recovery. Core code is not part
of a data backup; reinstall Core from a signed package.

## 8. Backup format

```text
backup-<timestamp>/
├─ manifest.json
├─ data/
│  ├─ core.db
│  └─ blobs/
└─ apps/
   ├─ installed.json
   └─ <slug>/data/
```

`manifest.json`:

```json
{
  "format": "loomsci-backup/1",
  "created_at": "...",
  "core_version": "...",
  "core_api": "core/1",
  "apps": [{"slug": "report", "version": "...", "data_namespace": "app_report"}],
  "files": [{"path": "data/core.db", "sha256": "...", "bytes": 0}]
}
```

Rules:

- SQLite backup uses a consistent snapshot (`VACUUM INTO` or checkpoint+copy).
- Write to a temporary directory, verify, then atomically rename.
- Never overwrite an existing backup.
- No secrets or tokens in the manifest.

## 9. Restore modes

v0 supports only:

```text
--new       restore into an empty workspace (default)
--replace   replace an existing workspace only with explicit --force
```

No partial merge in v0.

Restore behavior:

1. validate manifest and every file hash;
2. extract to a temporary workspace;
3. verify Core DB opens and app manifests parse;
4. if all pass, swap into place;
5. on failure, leave the current workspace untouched;
6. regenerate `local.token`;
7. do not start apps automatically if their versions are incompatible.

## 10. App version mismatch

- Restore data even if the app version differs; mark app as `needs_install` or
  `needs_update`.
- Core starts without that app.
- App data remains untouched until the user installs a compatible version.
- A future migration tool may upgrade app data; v0 does not auto-migrate.

## 11. Uninstall

- App uninstall removes code, keeps `apps/<slug>/data/` by default.
- `remove_data` requires explicit confirmation.
- Core uninstall keeps `data/` and `apps/*/data/`; `--purge` removes them only
  with explicit confirmation.

## 12. Acceptance

1. Core DB + blob + app DB restore into a clean workspace.
2. Restore preserves item ids, tags, blobs, and app relations.
3. `local.token` is not restored; a new token is generated.
4. Truncated backup is rejected before workspace swap.
5. App version mismatch does not delete data.
6. App uninstall keeps data.
7. Backup excludes venvs, logs, code by default.
8. Backup manifest lists every file with sha256 and bytes.
9. Restoring into a non-empty workspace requires `--force`.
10. A failed restore leaves the existing workspace unchanged.
