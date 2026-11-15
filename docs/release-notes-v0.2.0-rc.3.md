# LoomSci Core 0.2.0-rc.3 — release notes

Status: pre-release candidate. Not a public-beta declaration.

## Scope

This candidate closes the P0 content-lifecycle gaps required by
[PRODUCT.md](../PRODUCT.md): delete safety, tag density, item detail placement,
and attachment presentation. It is a user-authorized P0 scope closure, recorded
as an explicit exception to release Gate 0. No new product domain was added.

## Changes

- Soft delete, Trash, restore, and hard delete with blob cleanup.
- Schema v2 (`items.deleted_at`) with a `core.db.pre-v2-*` copy before migration.
- Trashed items are excluded from lists, search, tag counts, and tag pages.
- App-scoped tag counts are computed in SQL.
- Item detail opens in the main center area; the right rail is hidden.
- Tag cloud is capped at 20 tags; a searchable full tag page is available.
- Item cards show at most 3 tags plus `+N`.
- Attachment cards show icon, MIME, size, open/download; PDFs preview inline.
- Blob downloads stream through `send_file`; uploads are capped at 50 MB.

## Upgrade and rollback

- Existing schema v1 databases migrate to v2 on the first start.
- The pre-migration copy is `data/core.db.pre-v2-<timestamp>`.
- A newer schema still refuses to start.
- Keep the previous tag `v0.2.0-rc.2` and the pre-release backup for rollback.

## Gates

- [ ] source checks and full unit tests
- [ ] macOS fresh-venv acceptance
- [ ] macOS real-browser UI acceptance
- [ ] Windows fresh-venv acceptance
- [ ] release package SHA256
- [ ] tag and push after both machines pass
