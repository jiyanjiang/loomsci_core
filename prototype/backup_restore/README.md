# Backup/restore prototype

Not product code. Validates the data-only backup and restore contract.

```bash
python3 prototype/backup_restore/backup.py create --home <home> --out <backup>
python3 prototype/backup_restore/backup.py verify --backup <backup>
python3 prototype/backup_restore/backup.py restore --backup <backup> --home <target>
python3 prototype/test_backup_restore.py
```

Included:

- `data/core.db` (SQLite consistent backup)
- `data/blobs/`
- `apps/<slug>/data/`
- `apps/installed.json`
- `manifest.json` with sha256/bytes

Excluded:

- `local.token`
- logs
- venvs
- app code
- caches

Tested:

```text
macOS:   PASS
Windows: PASS
```

Cases:

- backup + verify
- restore into a clean workspace
- data preserved
- token regenerated
- non-empty target requires `--force`
- truncated backup rejected
- failed restore leaves the target unchanged

Not yet tested:

- app version mismatch
- `--with-code`
- partial restore
- large blob store
