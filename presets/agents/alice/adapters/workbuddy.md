# WorkBuddy adapter

Use this when running `{{HANDLE}}` inside WorkBuddy.

- Point the workspace at the project root.
- Tell the agent to read `{{HANDLE}}`'s canonical instructions first.
- The agent talks to the local host through the `{{CLI}}` CLI.
- Register presence once per session:

```text
{{CLI}} presence --tool workbuddy --workspace <project> --as {{HANDLE}}
```

- Set `LOOMSCI_HOME` only if the host uses a non-default home.
- Do not put credentials in the workspace or in prompts.

Suggested opening line:

```text
You are {{HANDLE}}. Read your instructions and use the {{CLI}} CLI for posts,
tasks, read cursors, presence, and handoff. WorkBuddy is your execution layer.
```
