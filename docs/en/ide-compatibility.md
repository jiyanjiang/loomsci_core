# IDE compatibility and add-on contract

LoomSci is editor-agnostic: Core exposes a loopback HTTP API, a CLI, and a
browser UI. No editor plugin is required. Editor integrations must use the CLI
or public `/v1` API; they must not import Core internals.

## Compatibility matrix

| IDE / editor | Integration | Status | Notes |
|---|---|---|---|
| Terminal (any shell) | `loomsci` CLI | Verified | A/B beta.20: status, search, projects, add-ons |
| Browser | `http://127.0.0.1:8790/app/` | Verified | Loopback only; no remote bind |
| VS Code | Terminal/task calling CLI; web UI in simple browser | Contract-compatible | No extension shipped |
| Cursor | Terminal/task calling CLI | Contract-compatible | Same CLI path as VS Code |
| Windsurf | Terminal/task calling CLI | Contract-compatible | Same CLI path |
| JetBrains IDEs | External Tool calling CLI | Contract-compatible | No plugin shipped |
| Zed | Terminal task | Contract-compatible | CLI only |
| Neovim / Vim | `:!loomsci ...` or terminal buffer | Contract-compatible | CLI only |
| Emacs | `shell-command` / `vterm` | Contract-compatible | CLI only |
| Xcode | Run Script / external terminal | Contract-compatible | CLI only; macOS |

"Contract-compatible" means the integration uses only stable interfaces; it has
not been exercised inside that IDE. A plugin should be added only when a real
workflow needs editor-native UI.

## Integration rules

- Call `loomsci` from the project home; do not write directly to `data.db`.
- Use `--json` for machine-readable CLI output where available.
- Use `/v1` with `X-Loomsci-Agent`; respect `api=core/1`.
- Do not bind Core or add-ons to non-loopback addresses.
- Do not store API keys in editor settings or repository files.
- Do not execute project application code from an IDE task.

## Add-on manifest contract

Run:

```bash
loomsci addon contract
loomsci addon contract --json
```

Required fields:

```text
name, version, api, package, entry, port, health
```

Optional fields:

```text
requires, routes, storage, jobs, nav, preserve
```

Rules:

- `api` must be `core/1`.
- `package` must be an importable directory name under `packs/`.
- `entry` must name a Python module in that package.
- `port` is the add-on's loopback port; `health` is its HTTP health path.
- `requires` can reference Core or another add-on with `>=`.
- Installed data lives in `packs/<package>/data/` and survives `addon update`.
- Core never imports add-on code; add-ons use public `/v1` APIs.
- A missing add-on must not prevent Core from starting.
