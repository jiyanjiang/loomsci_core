---
id: BUG-0003
title: ui-shell /app pages return 404
status: fixed
severity: P2
surface: ui-shell
reported: 2026-11-11
---

# BUG-0003 · ui-shell /app pages return 404

## Reproduction

Open:

```text
http://127.0.0.1:8790/app/posts
```

## Expected

The ui-shell workspace opens on the Posts view. The nav selects Tasks,
Memory, Inbox, and Site at their matching URLs.

## Actual

The ui-shell static server only served `/` and returned 404 for `/app` and
`/app/<view>`.

## Fix

- The server serves `index.html` for `/app` and the five view paths.
- The client reads the initial view from the path.
- Nav clicks use `history.pushState`; `popstate` restores the path view.
- Query-based post detail (`/app/posts?post=<id>`) remains supported.

Verified:

```text
/app/posts 200
/app/tasks 200
/app/memory 200
/app/inbox 200
/app/site 200
```

## Status

Fixed in `0.1.0-beta.4`. Open count: 0/10.
