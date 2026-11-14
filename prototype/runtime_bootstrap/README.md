# Runtime bootstrap prototype

Not product code. Validates the Python 3.12 + `uv` runtime contract on macOS
and Windows.

```bash
# macOS
LOOMSCI_UV=/path/to/uv ./prototype/runtime_bootstrap/bootstrap.sh --home /tmp/loomsci-runtime

# Windows
powershell -File prototype/runtime_bootstrap/bootstrap.ps1 `
  -TargetHome C:\Temp\loomsci-runtime -Uv C:\path\to\uv.exe
```

Steps:

1. detect `uv`
2. install managed Python 3.12 into `<home>/runtime/python`
3. create `<home>/venv`
4. write `<home>/runtime.json`
5. print the runtime/venv paths

Offline mode:

- `--offline` / `-Offline` sets `UV_PYTHON_DOWNLOADS=never`
- it fails if Python 3.12 is not already in the managed runtime directory
- production offline installers must bundle Python/wheels

Tested:

```text
macOS:   PASS (online install, offline reuse, idempotent second run)
Windows: PASS (online install, offline reuse)
```

Not tested:

- downloading `uv` itself on a machine without `uv`
- offline bundle with preloaded Python/wheels
- installing Core dependencies after venv creation
