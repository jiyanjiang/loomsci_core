# Signing/trust prototype

Not product code. Validates the M0 trust model:

```text
root key
├─ release cert → core/app packages
└─ content cert → content packs
```

Files:

- `sign_manifest.py` — simple manifest signing
- `trust.py` — cert chain, role, expiry, revocation, signature, payload
- `test_signing_matrix.py` — S1–S12 cases

Run:

```bash
python3 prototype/test_signing.py
python3 prototype/test_signing_matrix.py
```

Status:

```text
macOS:   S1–S12 PASS
Windows: S1–S12 PASS
```

Known gap:

- Cert files are a prototype format, not final distribution format.
- The installer copies only the payload; full Core package layout is next.
- Root key pinning and Authenticode/notarization are not implemented.
