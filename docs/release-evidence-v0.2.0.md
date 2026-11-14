# Release evidence: v0.2.0 Core Web UI

Status: candidate, not public beta yet.

## A machine — macOS real browser

Artifact: `loomsci_core-0.2.0-a728c36.zip`
SHA256: `5026702a0af1e8e0745126d905bbcff66aa88840af2bf5b869625b33563ef12b`

- `/` loads a usable Core UI; no horizontal overflow at 390px
- compose panel no longer stretches to list height
- markdown headings, bold, code, tables PASS
- KaTeX inline and block math PASS
- clipboard image paste shows a thumbnail before upload PASS
- pasted image uploads and renders inline PASS
- create item without title PASS
- list cards open an item detail view PASS
- detail renders full markdown PASS
- markdown attachments render nested and open by default PASS
- attachment names are SHA-256 short names PASS
- image thumbnails are uniform 120x120 / 96x96 PASS
- image gallery: next/previous/loop/close PASS
- tag cloud shows counts and filters the list PASS
- search PASS
- inline edit PASS
- delete PASS
- backup button PASS
- settings: username, API key, language, fingerprint, rotate PASS
- language switch to English PASS
- restart Core, items persist PASS
- API remains protected by local token

## B machine — Windows 10

Host: `taa-win` / `192.168.101.113`

- archive SHA256 PASS
- clean venv, 7 tests PASS
- CLI start/stop PASS
- Core start survives the SSH session (detached Windows process) PASS
- `/` returns 200 and contains the UI
- `/assets/app.js` returns 200
- headless Chrome screenshot captured at 1280x900
- CDP mouse clicks at 1280x900: create PASS, open detail PASS, open settings PASS
- tag cloud renders; tag-filter click still not marked PASS
- gallery click-through not yet run on B
- `ROUND1_WINDOWS_020_OK`

Remaining B gates: tag-filter click and gallery click-through.

## Remaining public-beta gate

```text
Windows real-browser acceptance
```
