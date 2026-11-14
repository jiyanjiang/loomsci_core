# beta.28 → Core v0 migration plan

- Status: M0 draft, 2026-11-14
- Source: `0.1.0-beta.28` SQLite workspace
- Target: Core v0 workspace + Report/Project app databases
- Mode: safe, read-only source; new workspace first
- Platforms: macOS and Windows
- Prototype status: dry-run + apply passed on A (48 posts) and B (278 posts)

## 1. Principle

The beta.28 workspace is **never modified in place** by the first migration.
The tool reads it, writes a new workspace, verifies counts and hashes, and only
then may the user switch to it.

```text
beta.28 workspace (read-only)
→ temp Core v0 workspace
→ Report DB / Project DB
→ legacy archive
→ verify
→ atomic switch (optional)
```

If anything fails, the source workspace remains usable.

## 2. Current data counts

From the A-machine beta.28 DB:

```text
posts                 48
post_summaries         8
tasks                  4
facts                  1
attachments           13
mentions               1
reads                  1
presence               1
projects               1
project_sources        1
project_entries     3,586
project_schemas        3
project_apps           1
project_evaluations    1
tags                   0
post_tags              0
tag_aliases            0
```

The migration must be count-driven, not hard-coded to these numbers.

## 3. Target ownership

| beta.28 | Target | Rule |
|---|---|---|
| `posts` | Core `items` | type `report.note`; preserve id/body/meta |
| `attachments` | Core `blobs` | preserve id, filename, content_type, sha256, bytes |
| `post_tags` / `tags` | Core `item_tags` | preserve names/source |
| `facts` | Core `items` | type `project.fact`; metadata claim fields |
| `projects` | Project app DB + Core projection | `project.project` item |
| `project_sources` | Project app DB | reference project id |
| `project_entries` | Project app DB | batch insert; 3,586 rows |
| `project_schemas` | Project app DB | reference project id |
| `project_apps` | Project app DB | reference project id |
| `project_evaluations` | Project app DB | reference project id |
| `tasks` | Project app DB | optional `project.task` projection |
| `mentions` | legacy archive | not migrated |
| `reads` | legacy archive | reading state may be rebuilt |
| `presence` | legacy archive | ephemeral |
| `post_summaries` | legacy archive | **not migrated** |
| `tag_aliases` | legacy archive | app may rebuild later |
| FTS tables | rebuilt | derived; never copy |
| `schema_migrations` | legacy archive | new ledger starts at v0 |

## 4. Field mapping

### posts → items

```text
items.id            = posts.id                    # keep stable links
items.app           = "report"
items.type          = "report.note"
items.title         = ""                          # posts had no title
items.body          = posts.body
items.metadata_json = {
  "legacy_kind": posts.kind,
  "legacy_author": posts.author,
  "thread_id": posts.thread_id,
  "parent_id": posts.parent_id,
  "legacy_meta": posts.meta_json,
  "source": "beta.28"
}
items.created_at    = posts.created_at
items.updated_at    = posts.created_at
```

### attachments → blobs

```text
blobs.id            = attachments.id
blobs.item_id       = attachments.post_id
blobs.filename      = attachments.filename
blobs.content_type  = attachments.content_type
blobs.bytes         = attachments.bytes
blobs.sha256        = attachments.sha256
blobs.created_at    = attachments.created_at
```

Copy bytes from `home/blobs/<id>` to new `data/blobs/<id>`.
Verify sha256 and bytes after copy.

### facts → items

```text
items.id            = facts.id
items.app           = "project"
items.type          = "project.fact"
items.title         = facts.claim
items.body          = facts.evidence
items.metadata_json = {
  "project": facts.project,
  "source": facts.source,
  "status": facts.status,
  "confidence": facts.confidence,
  "created_by": facts.created_by,
  "reviewed_by": facts.reviewed_by,
  "legacy_tags": facts.tags
}
```

### projects → Project DB + Core projection

Project app tables keep all fields:

```text
id, code, name, description, type, status, machine_id,
review_status, completeness, maturity, commercial_potential,
direction, review_notes, reviewed_at, reviewed_by,
created_at, updated_at
```

Core projection:

```text
items.id   = "project:" + projects.id
items.app  = "project"
items.type = "project.project"
items.title= projects.name
items.body = projects.description
items.metadata_json = review fields + code + machine_id
```

### project_* tables

Keep original rows in Project app DB, foreign keys unchanged:

```text
project_sources
project_entries
project_schemas
project_apps
project_evaluations
```

`project_entries` is the largest table; insert in batches of 500 inside a
transaction. Do not create one Core item per file.

### tasks

Project app DB table preserves all fields. A `project.task` Core projection is
optional; v0 defaults to **no projection** to avoid search noise. If enabled,
use `items.id = "task:" + tasks.id`.

## 5. Legacy archive

Unmapped data is exported to:

```text
legacy/
  post_summaries.jsonl
  mentions.jsonl
  reads.jsonl
  presence.jsonl
  tag_aliases.jsonl
  schema_migrations.json
  manifest.json
```

Rules:

- JSONL, one row per line, UTF-8.
- No secrets.
- Archive is included in the new workspace backup.
- Not imported into Core APIs.
- `post_summaries` is not used by Core v0; it remains available for audit.

## 6. Migration tool behavior

```bash
loomsci migrate-v0 \
  --from <beta28-home> \
  --to <new-core-home> \
  --dry-run
```

`--dry-run`:

- inspect source schema and counts
- list mapped/unmapped tables
- estimate output size
- do not write anything

`--apply`:

1. require target to be empty
2. create temp workspace
3. copy blobs and verify hashes
4. insert items/tags in batches
5. create Report DB if Report app selected
6. create Project DB if Project app selected
7. export legacy archive
8. write `migration-report.json`
9. verify counts and hashes
10. atomically rename temp workspace to target
11. leave source untouched

No in-place upgrade in v0.

## 7. Verification

Required:

- posts count = items count for `report.note`
- attachments count = blobs count
- blob sha256/bytes match source
- facts count = `project.fact` items
- projects count = Project DB rows
- project_entries count preserved
- tasks count preserved
- source workspace byte-identical after migration
- no token copied
- new `local.token` generated
- search returns a known post after FTS rebuild
- migration report lists all counts and hashes

## 8. Failure and rollback

- Any blob hash mismatch → abort before switch.
- Any count mismatch → abort before switch.
- Source DB is opened read-only.
- Temp workspace is removed on failure.
- Existing target is never overwritten.
- If switch fails, source remains the active workspace.

## 9. Windows and macOS specifics

- Use `sqlite3` backup/read-only URI for consistent reads.
- Handle spaces and Unicode in workspace paths.
- Windows file locks: never open source DB for write.
- Preserve case-sensitive IDs exactly.
- Copy blobs with `shutil.copy2`; verify after copy.
- Test on both platforms with a copy of the beta.28 workspace.

## 10. Acceptance

1. Dry-run lists all tables and counts.
2. Apply on macOS produces expected counts.
3. Apply on Windows produces expected counts.
4. 3,586 project entries preserved.
5. Blob hashes match.
6. Legacy archive contains summaries/mentions/reads.
7. No `post_summaries` rows in Core tables.
8. Source workspace unchanged (hash before/after).
9. Migration rerun against a different target is idempotent.
10. A failed migration leaves no target workspace.
11. Search works after migration.
12. New token is generated.

## 11. Open decisions

- whether old `posts` keep `author` in metadata or become app DB rows
- whether `facts` belong to Report or Project by default
- whether `tasks` get Core projections
- whether `project_entries` need a separate DuckDB/parquet export for scale
- whether `--replace` should exist at all in v0
