# AGENTS.md · instructions for AI IDE agents

This repository is a **preview seed** of `loomsci_core`. There is no runnable
host yet. Do not invent installation commands or claim features are shipped.

## If you are asked to work on this repository

- Read `README.md`, `docs/en/architecture.md`, and `docs/en/roadmap.md` first.
- Keep changes inside the current roadmap phase. Do not add product features
  that are not in the roadmap without an accepted design note.
- Do not add credentials, tokens, private keys, real user data, or absolute
  user-home paths.
- Keep user-facing text bilingual (`zh-CN` and `en`).
- Run `python scripts/check_public_tree.py` before proposing a change.

## Future runtime contract (planned)

When the host exists, agents will interact through the `loomsci` CLI or local
HTTP, using the identity handle `<agent>.<owner>` (for example
`alice.jiyanjiang`). The host will own the local boundary, post bus, tasks,
memory, and export. The IDE remains responsible for model calls and execution.

This section describes the target contract; it is not implemented yet.
