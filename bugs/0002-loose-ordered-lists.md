---
id: BUG-0002
title: Loose ordered lists restart numbering
status: fixed
severity: P2
surface: ui-shell, collab, notify
reported: 2026-11-11
---

# BUG-0002 · Loose ordered lists restart numbering

## Reproduction

```markdown
1. 这是第一

2. 这是第二
```

## Expected

One ordered list; the blank line makes it a loose list, not two lists:

```html
<ol><li>这是第一</li><li>这是第二</li></ol>
```

## Actual

Before the fix, each blank line closed the active list:

```html
<ol><li>这是第一</li></ol><ol><li>这是第二</li></ol>
```

The numbering restarts at 1, so it does not read as an ordered list.

## Root cause

The renderers closed the list on every blank line without looking at the next
non-empty line. A blank line between two list items is valid Markdown.

## Fix

- ui-shell looks ahead to the next non-empty line.
- collab and notify defer closing with a `pendingBlank` flag.
- A blank line keeps the same list type open; a heading, paragraph, different
  list type, or end of input closes it.

Verified live:

```text
ui:     <ol><li>这是第一</li><li>这是第二</li></ol>
collab: <ol><li>这是第一</li><li>这是第二</li></ol>
notify: <ol><li>这是第一</li><li>这是第二</li></ol>
```

## Status

Fixed in `0.1.0-beta.3` under the owner's direct report. Open count: 0/10.
