---
id: BUG-0001
title: Ordered lists collapse into a paragraph
status: open
severity: P2
surface: collab, notify
reported: 2026-11-11
---

# BUG-0001 · Ordered lists collapse into a paragraph

## Terminology

- **Ordered list**: `1.`, `2.`, `3.` → semantic `<ol>`.
- **Unordered list**: `-`, `*`, `+` → semantic `<ul>`.

This report is only about ordered lists. The unordered-list path works in the
same renderer; see the live checks below.

## Reproduction

Input:

```markdown
这是一个列表

1. 第一个改进
2. 第二个改进
```

## Expected

```html
<p>这是一个列表</p>
<ol>
  <li>第一个改进</li>
  <li>第二个改进</li>
</ol>
```

## Actual

Collab and notify render the ordered list as one paragraph:

```html
<p>这是一个列表</p>
<p>1. 第一个改进 2. 第二个改进</p>
```

The numbers are not list markers and the items are not separate rows.

`ui-shell` renders the same input correctly:

```html
<p>这是一个列表</p>
<ol><li>第一个改进</li><li>第二个改进</li></ol>
```

## Scope

- `addons/collab/web/app.js` — `markdown()` only recognizes `-` / `*` bullets
- `addons/notify/web/app.js` — same unordered-only branch
- `addons/ui_shell/web/app.js` — not affected

## Evidence

- Screenshot: `bugs/evidence/BUG-0001.png`
- Live check: `markdown(...)` in the collab page at `http://127.0.0.1:8792/`
- Live check: `markdown(...)` in the notify page at `http://127.0.0.1:8793/`
- Both returned the paragraph form above.
- `ui-shell` at `http://127.0.0.1:8790/` returned `<ol>`.
- Unordered control on collab:
  `markdown("- 第一个\n- 第二个")` returned
  `<ul><li>第一个</li><li>第二个</li></ul>`.

## Root cause

Both affected renderers only test for unordered markers:

```js
if (/^\s*[-*]\s+/.test(line)) { ... }
```

Lines matching `^\s*\d+\.\s+` fall through to `para.push(line.trim())`.
A blank line flushes the paragraph, but the ordered items are then joined with
spaces into a second paragraph.

## Fix scope

Add an ordered-list branch, track the active list type (`ol`/`ul`), and close
the correct tag at blank lines, headings, code fences, and end of input.

Do not merge a fix before the bug gate reaches 10 open reports.

## Status

Open. Count: 1/10.
