# Release evidence: v0.2.0 Core Web UI

Status: candidate, not public beta yet.

## A machine — macOS real browser

Artifact: `loomsci_core-0.2.0-b3b478d.zip`  
SHA256: `2932bdf3cb5b78e6e4f0e4c71abe4577b7e30bae06f4127061647672fc3ff236`

- `/` loads a usable Core UI
- markdown headings, bold, code, tables PASS
- KaTeX inline math `$...$` and block `$$...$$` PASS
- clipboard image paste adds a pending attachment with a visible thumbnail PASS
- pasted image uploads and renders inline PASS
- create item without title PASS
- list immediately shows item PASS
- search PASS
- inline edit PASS
- delete PASS
- tags PASS
- file attachment PASS
- backup button PASS
- restart Core, items persist PASS
- API remains protected by local token

## B machine — Windows 10

Host: `taa-win` / `192.168.101.113`

- archive SHA256 PASS
- clean venv, 7 tests PASS
- CLI start/stop PASS
- `/` returns 200 and contains the UI
- `/assets/app.js` returns 200
- `ROUND1_WINDOWS_020_OK`

Not yet done on B: a real browser click-through of markdown, KaTeX, clipboard
paste, edit, and attachment rendering.

## Remaining public-beta gate

```text
Windows real-browser acceptance
```
