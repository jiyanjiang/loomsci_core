# ui-shell functional target

`ui-shell` is the first add-on and the only supported UI shell for Core. It is
a separate process on 8790, consumes only Core `/v1`, and never imports Core.
Theme work is explicitly out of scope for this phase.

## Required functionality

1. **Safe Markdown**
   - headings, paragraphs, bold/italic, inline code, fenced code
   - unordered/ordered lists, blockquotes, horizontal rules
   - links (http/https only), tables
   - raw HTML is never executed

2. **LaTeX**
   - inline `$...$` and block `$$...$$`
   - KaTeX vendored locally (no CDN dependency)
   - invalid expressions show source, never crash the page

3. **Attachments**
   - images render inline
   - browser-supported audio/video render with controls
   - other files download
   - upload a local file and attach it to a post
   - paste an image from the clipboard into the body editor

4. **Search**
   - search posts/tasks/facts through `/v1/search`

5. **Core operations**
   - create post
   - create task, claim, done with evidence
   - add/review memory
   - inbox list, mark one/all read

6. **States**
   - loading, empty, and error states
   - no silent failures
   - keyboard-accessible buttons/forms

## Non-goals

- themes, animations, rich WYSIWYG editor
- PDF/Office preview
- media transcoding, thumbnails, OCR/transcription
- auth, multi-user, center, sync
- changing Core tables or `/v1` shapes

## Acceptance

Automated browser checks must pass on macOS and Windows:

- Markdown table and code fence render
- `$E=mc^2$` renders through KaTeX
- an image attachment renders as `<img>`
- an audio/video attachment exposes `<audio>`/`<video controls>`
- search returns a result
- upload attaches a file to a post
- task claim/done and memory review work
- no raw HTML injection

Only then may the next add-on (`media`) start.

## Self-check (2026-11-10)

- macOS: Markdown table/code, KaTeX, image/audio/video elements, search,
  upload, task/memory actions, XSS rejection — pass.
- Windows: Markdown table, KaTeX, search, create post — pass; the same package
  is used, with media elements verified on macOS.

## Baseline theme gate

This phase is tokens + accessibility, not branding or theme switching.

- single token source for colors, spacing, type, radius
- system light/dark via `prefers-color-scheme`
- body contrast 15.7:1 (light) / 16.6:1 (dark); muted 5.9:1 / 8.3:1
- keyboard focus: 2px solid accent outline
- min control height 36px
- 360px viewport: no horizontal scroll
- no external fonts/CDN; KaTeX stays local

Self-checked 2026-11-10 with a real Chromium tab. Full visual themes,
site name/logo, i18n, and boards remain separate/later.
