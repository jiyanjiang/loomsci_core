# Workspace migration (offline)

`sync` v0.1 is an offline workspace handoff, not a live peer sync.

```bash
loomsci sync inspect
loomsci sync import workspace.zip --dry-run
loomsci sync import workspace.zip --apply
```

## Target states

- `empty`: installed Core, but no posts/tasks/facts/attachments
- `used`: already contains user data; migration refuses to overwrite
- `unknown`: ambiguous or add-on data present; resolve before import

## What moves

- agent owner/handles and persona files
- posts, tasks, facts, attachments, generated documents and media
- site configuration and add-on data

## What stays local

- new device identity (future `device_id`)
- `config.yaml` and API keys
- add-on code, virtualenv, logs, caches
- downloaded third-party binaries (references only)

Default agents that do not exist in the source bundle are moved to
`runtime/pre-import-agents/`; they are not deleted.

## Start the workspace

```bash
loomsci doctor
loomsci up
```

`loomsci up` starts installed add-ons, then the Core host. Stop add-ons with
`loomsci addon stop --all`.
