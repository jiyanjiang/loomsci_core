# Release evidence: v0.2.0 Core Web UI

Status: `v0.2.0-rc.1` pre-release. Not public beta. Help: [help](en/core-v0/help.md).

## A machine — macOS real browser

Artifact: `loomsci_core-0.2.0-55749e0.zip`
SHA256: `39a8d0af93ae6e464eac90d54b8d3024c1a5eaea9275637da32bf88bc52bd9e0`

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
- headless Chrome screenshot captured at 1280x900 (three-column layout)
- CDP mouse clicks at 1280x900: create PASS, open detail PASS, open settings PASS
- final CDP mouse test: gallery open PASS, next/prev PASS, tag-filter click PASS, settings PASS
- screenshots: list/detail/gallery/tag/settings at 1280x900
- `ROUND1_WINDOWS_020_OK`

P0 B interaction gate: PASS.

## Remaining public-beta gate

```text
Windows real-browser acceptance
```

## P0 hardening verification

Artifact: `loomsci_core-0.2.0-7e83f02.zip`
SHA256: `6704f0e800ac54e75b55d25bf1dca3cb5c86dd8da7f67b17b9036803ec57d196`

- UI uses HttpOnly SameSite=Strict cookie; no token in HTML
- schema version `1`; pre-migration backup; future schema rejected
- backup verify + restore UI
- 9 tests PASS
- B machine clean venv + 9 tests + UI HTTP PASS
- B tag-cloud and gallery click-through PASS
