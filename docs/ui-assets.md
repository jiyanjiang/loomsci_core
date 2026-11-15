# UI asset migration: 8790 -> 8795

Source: historical `addons/ui_shell` / `core/app.py` implementation.  
Destination: minimal `loomsci_core` Web UI.

The goal is to keep the clean Core substrate, not restore the whole 8790 product.

## Migrated

| Asset | Destination | Reason |
|---|---|---|
| markdown renderer | `loomsci_core/web/app.js` | headings, bold, code, tables, links |
| KaTeX assets + auto-render | `loomsci_core/web/vendor/katex` | inline and block LaTeX |
| clipboard image paste | `loomsci_core/web/app.js` | paste, pending chip, upload |
| attachment rendering | `loomsci_core/web/app.js` | inline image / file link |
| markdown-oriented layout | `loomsci_core/web/index.html`, `style.css` | body-first, no title field |

## Not migrated

- projects
- tasks
- memory / facts
- inbox
- site settings
- full i18n
- legacy `/v1/posts` API
- legacy Core server and add-on framework
- installer, updater, marketplace

## Intentional difference

The new UI has no title field. An item is Markdown body + tags + attachments.
The API still accepts `title` for compatibility, but the Core UI does not require
or display it.

## Rule

Migrate a behavior only when it is required by the Core product definition.
Do not copy whole modules from 8790. If a feature needs projects, tasks, or
memory, it belongs to a future App, not this Core UI.

## Second migration pass

| Asset | Destination | Reason |
|---|---|---|
| item detail route | `app.js` | open one item instead of one long column |
| gallery lightbox | `app.js` | looped next/previous image viewing |
| tag cloud | `app.js` | Top 20 tags by count plus full tag page |
| pagination | `app.js` | 20 items per load |
| settings page | `app.js` | username, API key, language, local fingerprint |
| i18n dictionary | `app.js` | Chinese / English |
| SHA-256 attachment names | `store.py`, `app.js` | stable, non-sequential attachment labels |

The SPA is still Core-only. Projects, tasks, memory, inbox, site settings and
the old `/v1/posts` API remain out of scope.
