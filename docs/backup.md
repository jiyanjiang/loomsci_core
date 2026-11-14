# Pre-shrink backup

The full tree before the minimal cut is preserved in Git:

```text
Branch: backup/pre-shrink-0bbc4ad
Tag:    pre-shrink-2026-11-14
Commit: 0bbc4ad
```

It contains the 449-file, ~36k-line state, including the old beta product,
prototype installer/updater, migration tools, reports, styles, and old docs.

## Recover

```bash
git fetch origin
git switch -c recover/pre-shrink backup/pre-shrink-0bbc4ad
```

Or inspect a single file without switching:

```bash
git show pre-shrink-2026-11-14:path/to/file
```

## Do not merge blindly

Do not merge the full backup into `minimal-v0`. Restore only a file that the
minimal public beta actually needs, with a reason and a test.

## Current minimal tree

```text
Branch: minimal-v0
Commit: dec6471
Files:  35
```

The minimal tree keeps items, tags, blobs, FTS, auth, App Host
install/start/stop, backup/restore, SDK, one example app, tests, and minimal
docs.
