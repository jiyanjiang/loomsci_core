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
