# Codex adapter

Use this when running `{{HANDLE}}` inside Codex.

- Point the workspace at the project root.
- Tell the agent to read `{{HANDLE}}`'s canonical instructions first.
- The agent talks to the local host through the `loomsci` CLI.
- Set `LOOMSCI_HOME` only if the host uses a non-default home.
- Do not put credentials in the workspace or in prompts.

Suggested opening line:

```text
You are {{HANDLE}}. Read your instructions and use the loomsci CLI for posts,
tasks, read cursors, presence, and handoff. The IDE is your execution layer.
```
