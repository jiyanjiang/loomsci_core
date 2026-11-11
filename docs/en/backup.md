# Backup asset boundary

`loomsci backup inspect` is a read-only inventory. It does not create, delete,
or rewrite files.

## Buckets

| Bucket | Default | Examples |
|---|---|---|
| assets | included | SQLite data, agent persona, notes/posts, generated media, program/assets, add-on data |
| references | metadata only | downloaded PDFs/papers, ebooks, datasets, archives |
| derived | excluded | thumbnails, caches, generated preview files |
| excluded | excluded | code packages, virtualenvs, logs, runtime, temp files |
| secrets | never included | keys, tokens, passwords, `.env`, credential config |

`references` binaries are excluded from the asset backup, but their metadata can
be represented by `references.json` in a future bundle.

## Commands

```bash
loomsci backup inspect
loomsci backup inspect --json
loomsci backup create --out assets.zip
loomsci backup show assets.zip
loomsci backup restore assets.zip --to <empty-home>
loomsci backup restore assets.zip --to <empty-home> --apply
```

A secret hit blocks a future backup export or requires explicit redaction; the
inventory never prints the secret value.

## Not part of backup

- third-party PDFs/papers (cite/index instead)
- API keys, passwords, private keys, tokens
- virtualenvs, node_modules, caches, logs, runtime state

## Storage lifecycle

```bash
loomsci storage report
loomsci storage duplicates
loomsci storage dedupe --apply
loomsci storage prune --older-than 3600
loomsci storage prune --older-than 3600 --apply
loomsci storage compact --apply
```

`dedupe` replaces duplicate blobs with hardlinks; `prune` removes only orphan
blobs older than the threshold; `compact` requires `--apply`. Run a backup
before destructive maintenance.

```bash
loomsci backup verify assets.zip
loomsci backup prune --dir ./backups --keep 5
loomsci backup prune --dir ./backups --keep 5 --apply
```

## Provenance

```bash
loomsci asset list --unclassified
loomsci asset classify <attachment-id> --origin generated
loomsci asset classify <attachment-id> --origin downloaded
```

`origin=generated|authored` binaries are included, `origin=downloaded` binaries
are references only, and unknown documents default to inclusion for migration
safety.
