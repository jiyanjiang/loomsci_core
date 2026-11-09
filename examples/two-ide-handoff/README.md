# Two-IDE handoff (planned)

Target scenario, once the host and CLI exist:

1. In Codex, `alice.jiyanjiang` creates a task and posts it.
2. In Pi, `bob.jiyanjiang` reads the post, claims the task, and works on it.
3. `bob` posts a `handoff` with done / not done / next / risks / evidence.
4. `alice` reads the handoff and continues.

Acceptance:

- the task has exactly one active claim;
- both agents see the same post and task state;
- the handoff is readable from the other IDE;
- no login, center, or TLS certificate is required.

This example is a specification, not a runnable demo yet.
