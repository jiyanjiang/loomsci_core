# Release evidence: v0.2.0-rc.4

Status: pre-release candidate. Not a public-beta declaration.
Scope: TAA-style two-stage item interaction (right-rail preview -> full view).

Candidate code commit: `3b4f4ad`.

## Source and package

```bash
node --check loomsci_core/web/app.js
python -m unittest discover -s tests -q          # 15 tests OK
python -m compileall -q loomsci_core examples tests
git diff --check
```

Package:

```text
loomsci_core-0.2.0-rc.4.zip
SHA256 77bd9e09ca6080510ecd4f1b424a32ca84c3d2c934703c80bc007476d9139752
```

## A machine — macOS

Host: macOS 26.2, arm64, Python 3.12.13.
Fresh venv with Flask 3.1.3 and cryptography 50.0.2.

```text
python -m unittest discover -s tests -q  -> 15 tests OK
```

Real-browser regression at 1440x900:

```text
initial layout: 732px list / 440px right rail
click item: hash #/item/<id>; list stays; right preview; selected=1
preview scrollY: 400 -> 400
preview toolbar: 打开全文 / 回到列表 / 删除
open full: #/item/<id>/full; list hidden; right hidden; itemView 980px; scroll 0
full toolbar: ← 返回 / 删除
← 返回: preview restored; scrollY 400; selected 1
回到列表: #/; scrollY 400; selected 0; empty placeholder visible
browser Back from full: preview restored; scrollY 400
```

## B machine — Windows

Host: Windows 10.0.19045.0, Python 3.12.9.
Fresh venv with Flask 3.1.3 and cryptography 50.0.2.

```text
python -m unittest discover -s tests -q  -> 15 tests OK (4.525s)
```

Headless Chrome 157 via CDP at 1440x900, against the packaged candidate:

```text
initial list: 20 cards
click item: hash #/item/<id>; list visible; right rail 440px; selected=1
preview scrollY: 400 -> 400
preview toolbar: 打开全文 / 回到列表 / 删除
open full: #/item/<id>/full; list/right hidden; itemView 980px; scroll 0
full toolbar: ← 返回 / 删除
← 返回: preview restored; scrollY 400; selected 1
回到列表: #/; scrollY 400; selected 0; empty placeholder visible
```

Package SHA256 verified on B before extraction.

## Result

`DUAL_MACHINE_RC4_OK`.

Tag/push intentionally not performed for this candidate; the previous
`v0.2.0-rc.3` tag remains the published release point.
