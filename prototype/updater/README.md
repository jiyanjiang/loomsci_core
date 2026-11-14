# Signed updater prototype

Not product code. Validates the C1 update chain:

```text
signed package
→ verify
→ backup
→ stop Core
→ atomic payload replace
→ start Core
→ health
→ rollback on failure
```

Run:

```bash
python3 prototype/test_updater.py
```

Tested:

```text
macOS:   PASS
Windows: PASS
```

Cases:

- valid signed package updates
- previous payload preserved
- backup created
- tampered package rejected before stop
- Core remains on the old payload after rejection

Caveat:

- The payload is a marker file, not the final Core package layout.
- The real installer must replace a full package and restart from the new code.
