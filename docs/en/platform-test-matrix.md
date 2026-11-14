# Platform test matrix · Core + Apps

- Status: M0 draft, 2026-11-14
- Mandatory platforms: macOS (A machine) and Windows (B machine)
- Rule: no single-OS waiver for Core platform gates

## 1. Hosts

```text
A  macOS arm64    primary development + Core host
B  Windows x64    second personal OS; install/update/path/locking tests
```

Both machines run the same signed package and the same contract tests.

## 2. M0 gates

| Area | Test | macOS | Windows |
|---|---|---|---|
| Process | install → start → health → stop → update → remove | required | required |
| Process | app crash/restart policy | required | required |
| Process | 30s health timeout | required | required |
| Runtime | uv-managed Python, no manual install | required | required |
| Runtime | per-app venv | required | required |
| Data | item + blob + app DB restore | required | required |
| Data | app update preserves data | required | required |
| Data | app remove preserves data | required | required |
| Signing | S1–S12 from `signing-trust.md` | required | required |
| Installer | clean install, no duplicate workspace | required | required |
| Installer | failed verify leaves no partial install | required | required |
| Paths | spaces, Unicode, long path, drive change | required | required |
| File lock | stop before replace/update | required | required |

## 3. Current status

```text
process contract prototype   macOS PASS   Windows PASS
signing prototype            pending     pending
backup/restore prototype     pending     pending
uv bootstrap                 pending     pending
Linux                        not required for M0; later
```

## 4. Test rules

- Use a clean/temporary workspace for every destructive test.
- Record OS version, arch, package sha256, and test timestamp.
- A Windows pass does not replace a macOS pass, and vice versa.
- A test that cannot run on one OS is not “passed”; it is `blocked`.
- No M0 exit until all required rows pass on both.

## 5. Evidence

Each run produces:

```text
reports/core_m0/<date>-<os>-<test>.json
```

with:

```json
{
  "os": "...",
  "arch": "...",
  "package_sha256": "...",
  "test": "...",
  "result": "pass|fail|blocked",
  "started_at": "...",
  "elapsed_ms": 0,
  "error": null
}
```
