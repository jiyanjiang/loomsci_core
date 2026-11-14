# Signing and trust contract · v0

- Status: M0 draft, 2026-11-14
- Scope: Core packages, official App packages, content packs
- Algorithm: Ed25519
- Platforms: macOS and Windows are first-class test targets

## 1. Goals

- A tampered package is rejected before extraction.
- A valid package verifies offline.
- Keys can rotate without breaking existing installs.
- A compromised key can be revoked.
- No partial install remains after verification failure.
- Users do not need an account or network to verify a local package.

## 2. Trust hierarchy

```text
Root key (offline)
├─ Release key   → Core packages, official App packages
└─ Content key   → content packs (never executable code)
```

For v0:

- one root key, one release key, one content key;
- official apps are signed by the release key;
- third-party app signing is deferred;
- root private key is offline, release/content private keys are CI-held.

## 3. Public-key distribution

Installer and Core ship:

```text
trust/root.pub
trust/release.cert
trust/content.cert
trust/revocations.json
```

- `root.pub` is the trust anchor; its fingerprint is printed in release notes.
- `release.cert` and `content.cert` contain the public key, key id, role, and
  validity window, signed by the root key.
- The installer pins the root fingerprint in source and verifies the Core
  package against the release cert.
- Core verifies App and content packages against the same trust directory.
- No public key is fetched from the network during installation.

## 4. Package format

```text
package/
├─ manifest.json
├─ manifest.sig
└─ payload/
```

`manifest.json` contains at minimum:

```json
{
  "kind": "core | app | content",
  "name": "...",
  "version": "...",
  "platform": "macos-arm64 | windows-x64 | any",
  "created_at": "...",
  "payload_sha256": "...",
  "payload_bytes": 0,
  "key_id": "..."
}
```

Signature:

- Ed25519 over canonical JSON bytes:
  `json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`
- detached `manifest.sig`, base64-encoded
- signature covers `manifest.json`; `payload_sha256` binds the payload
- verification checks signature, key role, validity, key id, payload hash, and
  payload size

## 5. Verification order

```text
1. read manifest + signature
2. find key by key_id in trust/
3. verify cert chain to pinned root
4. check key role (release/content)
5. check validity / revocation
6. verify manifest signature
7. verify payload_sha256 and payload_bytes
8. extract to temporary directory
9. verify extracted tree hash
10. atomically install
```

Any failure:

- stop before extraction or before swap;
- remove temporary files;
- keep the existing installation;
- report a specific error code.

## 6. Error codes

```text
signature_missing
signature_invalid
key_unknown
key_revoked
key_expired
key_role_mismatch
manifest_invalid
payload_hash_mismatch
payload_size_mismatch
payload_extract_failed
```

No generic “install failed” without a code.

## 7. Key rotation

- Release/content keys are rotated by issuing a new cert signed by the root.
- Old cert remains valid for an overlap window (at least two releases).
- Root key rotation:
  1. new root key signs a transition cert containing both fingerprints;
  2. installers pinning the old root accept the new root during overlap;
  3. next Core release pins the new root;
  4. old root is retired after the overlap.
- Every rotation is recorded in release notes.

## 8. Revocation

`trust/revocations.json` is signed by the root key:

```json
{
  "issued_at": "...",
  "keys": [{"key_id": "...", "reason": "compromised", "effective_at": "..."}]
}
```

- Core checks revocation before use.
- Offline installs use the bundled revocation list.
- Online update may refresh it, but absence of network must not block local use.
- A revoked key cannot sign new packages; already installed packages are not
  removed, but future updates with that key are rejected.

## 9. Platform notes

### Shared

- Ed25519 verification is OS-independent.
- File writes use atomic replace.
- No private key is written to the workspace, logs, or package.

### macOS

- v0 uses checksum + Ed25519; Apple notarization is a later distribution task.
- Installer must not rely on Gatekeeper bypass.
- `~/.loomsci` remains user-owned; no admin privilege required.

### Windows

- v0 uses checksum + Ed25519; Authenticode is a later distribution task.
- No admin privilege; install under the user profile.
- File locks require stop-before-replace.

## 10. Test matrix

All signing tests must pass on **macOS and Windows** before M0 closes.

| ID | Test | Expected |
|---|---|---|
| S1 | valid Core package | install succeeds |
| S2 | tampered manifest | `signature_invalid` |
| S3 | tampered payload | `payload_hash_mismatch` |
| S4 | missing signature | `signature_missing` |
| S5 | wrong key id | `key_unknown` |
| S6 | revoked key | `key_revoked` |
| S7 | expired cert | `key_expired` |
| S8 | content key signs executable app | `key_role_mismatch` |
| S9 | offline verify | succeeds without network |
| S10 | failed verify leaves no partial install | directory unchanged |
| S11 | rotated release key in overlap | old/new both verify |
| S12 | file truncation | rejected before extraction |

## 11. Acceptance

1. S1–S12 pass on macOS.
2. S1–S12 pass on Windows.
3. No private key appears in the repo, logs, or package.
4. A failed verification leaves the existing installation byte-identical.
5. The installer reports a specific error code.
6. The same signed package verifies on both platforms.
7. Content packs cannot be used to install code.
8. Root key fingerprint is documented in release notes.

## 12. Open questions

- v0 ships one release key or per-app keys?
- revocation refresh interval and offline grace;
- Authenticode/notarization timing for public non-technical users;
- third-party app signing policy.
