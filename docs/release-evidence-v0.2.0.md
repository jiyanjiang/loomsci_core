# Release evidence: v0.2.0 Core Web UI

Status: candidate, not public beta yet.

## A machine — macOS real browser

Artifact: `loomsci_core-0.2.0-f79d55a.zip`  
SHA256: `2a8b07cc1c0c1db59882a848c5f7472958c505d08d47240ebc5057d6672c2c7d`

- `/` loads a usable Core UI
- markdown headings, bold, code, tables PASS
- KaTeX inline math `$...$` and block `$$...$$` PASS
- clipboard image paste adds a pending attachment PASS
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
