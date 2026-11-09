# Release and upgrade

## Build a package

```bash
python scripts/build_release.py --out dist
```

Outputs:

```text
dist/loomsci_core-<version>.zip
dist/loomsci_core-<version>.zip.sha256
dist/latest.json
```

The zip contains `BUILD_INFO.json` and `upgrade-manifest.json`. The manifest
lists code entries that may be replaced and user data that must be preserved.

Signing is optional:

```bash
python scripts/build_release.py --out dist --signing-key /path/to/ed25519.raw
```

## Install

macOS / Linux:

```bash
bash install.sh --package loomsci_core-<version>.zip
```

Windows PowerShell:

```powershell
.\install.ps1 -Package .\loomsci_core-<version>.zip
```

Both installers keep code under `<home>/core` and data under `<home>/data`,
`<home>/agents`, `<home>/packs`, `<home>/logs`, and `<home>/runtime`.
A previous code tree is kept as `<home>/core.prev`.

## Upgrade / rollback

```bash
python scripts/upgrade.py --package loomsci_core-<version>.zip --home <home>
python scripts/upgrade.py --home <home> --rollback
```

The upgrade swaps only `core/`; data directories and `config.yaml` are never
modified. A failed swap restores the previous code tree automatically.
