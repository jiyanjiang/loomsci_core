# Release evidence: v0.2.0 Core Web UI

Status: candidate, not public beta yet.

## A machine — macOS real browser

Artifact: `loomsci_core-0.2.0-51d09bd.zip`
SHA256: `0d98593febd06d39d8b1efefff3cecf21e19479aa45b98a2f4d0b4677948f7ac`

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
- `/` returns 200 and contains the UI
- `/assets/app.js` returns 200
- `ROUND1_WINDOWS_020_OK`

Not yet done on B: real browser click-through of the SPA interactions.

## Remaining public-beta gate

```text
Windows real-browser acceptance
```
