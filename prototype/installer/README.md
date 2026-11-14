# uv-less installer prototype

Not product code. Validates that the installer can run with **no uv/python on
PATH**, using an explicit uv binary and a checksum file.

```bash
# macOS
env -i HOME=/tmp/loomsci-home PATH=/usr/bin:/bin \
  ./prototype/installer/install.sh \
  --home /tmp/loomsci-installer \
  --uv /tmp/uv-bundle/uv \
  --sha256 /tmp/uv-bundle/uv.sha256

# Windows
powershell -NoProfile -ExecutionPolicy Bypass -File install.ps1 `
  -TargetHome C:\Temp\loomsci-installer `
  -Uv C:\Temp\uv-bundle\uv.exe `
  -Sha256 C:\Temp\uv-bundle\uv.sha256
```

Verified:

```text
macOS:
  uv not on PATH          PASS
  uv checksum mismatch    reject
  offline first run       reject (no managed Python yet)
  online install          PASS
  offline second run      PASS

Windows:
  uv not on PATH          PASS
  online install          PASS
  offline second run      PASS
```

Not yet tested:

- downloading uv on a machine with neither uv nor a bundled uv
- signed uv/installer package
- Core dependency installation
- app install after Core bootstrap
