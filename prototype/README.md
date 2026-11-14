# Process contract prototype

Not product code. This validates the M0 process contract:

```text
install → start → health → stop → update → remove
```

It tests:

- per-app venv
- scoped token in the environment
- loopback health check
- pid/state file
- stdout/stderr logs
- data preservation on update/remove

Run:

```bash
python3 prototype/test_process_contract.py
```

Platform status:

- macOS: tested
- Windows: tested
- Linux: not yet tested

This is a prototype, not the final Core App Host.
