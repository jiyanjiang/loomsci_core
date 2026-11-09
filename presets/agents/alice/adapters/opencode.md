# opencode adapter

Use this when running `{{HANDLE}}` inside opencode.

- Start the session in the project root.
- Load the canonical instructions for `{{HANDLE}}`.
- Use `{{CLI}}` for the local bus; keep model calls inside the IDE.
- Register presence with:

```text
{{CLI}} presence --tool opencode --workspace <project> --as {{HANDLE}}
```

- Do not add credentials or absolute user-home paths to the workspace.
