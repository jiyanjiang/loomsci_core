# Release evidence: v0.2.0 Core Web UI

Status: candidate, not public beta yet.

## A machine — macOS real browser

Artifact: `loomsci_core-0.2.0-124096b.zip`  
SHA256: `d9bbca6e24e7e90f9a1d0ff07ad54cc77f48cd32648922c3461277e8c6c21feb`

- `/` loads a usable Core UI
- create item PASS
- list immediately shows item PASS
- search PASS
- inline edit PASS
- delete PASS
- tags PASS
- attachment upload and display PASS
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

Not yet done on B: a real browser click-through of create/edit/search/attachment.
Windows browser interaction is the remaining public-beta gate.

## Product status

The product definition now has a real UI surface:

```text
http://127.0.0.1:8795/
```

Do not publish `v0.2.0` as public beta until the Windows browser acceptance is
completed.
