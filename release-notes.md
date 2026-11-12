# loomsci_core 0.1.0-beta.15 · Public Beta

- Version: `0.1.0-beta.15`
- Package: `releases/loomsci_core-0.1.0-beta.15.zip`
- SHA256: `16fd27a02009a81566d968e25a897c6bba674037c200e12cac5c597c4f173077`

## API/schema contract

- Add `schema_version` plus a `schema_migrations` ledger using SQLite user_version.
- `/v1/health` and `/v1/version` expose `api_version=core/1` and `schema_version`.
- Add-on manifests are checked against `api=core/1`.

This release carries beta.14 security audit, beta.13 update checker, and beta.12
review gate.
