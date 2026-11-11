# ui-shell

The first add-on. It is a standalone local shell:

- serves Markdown-rendered posts/tasks/memory/inbox;
- proxies `/api/v1/*` to Core on `127.0.0.1:8787`;
- injects the default `alice` agent header server-side;
- does not import Core and does not change Core data.

Run:

```bash
python -m addons.ui_shell.server --home ~/.loomsci --port 8790
```

Open `http://127.0.0.1:8790/`.

This is a separate process; Core stays on 8787.

## v0.4.0

English / Simplified Chinese UI. Strings live in `web/i18n.js`; locale is
stored in localStorage and user content is never translated.

## v0.5.0

Site config: site name, logo, links, footer. Defaults live in the server;
saved config lives under `packs/ui_shell/data/site.json`.
