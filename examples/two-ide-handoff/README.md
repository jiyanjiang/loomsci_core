# Two-IDE handoff

Target scenario for the current local host:

1. In WorkBuddy, `alice.jiyanjiang` creates a task and posts it.
2. In opencode, `bob.jiyanjiang` reads the post, claims the task, and works on it.
3. `bob` posts a `handoff` with done / not done / next / risks / evidence.
4. `alice` reads the handoff and continues.

Acceptance:

- the task has exactly one active claim;
- both agents see the same post and task state;
- the handoff is readable from the other IDE;
- no login, center, or TLS certificate is required.

The CLI already supports the flow; this directory remains a scenario and
acceptance note, not a scripted GUI demo.
