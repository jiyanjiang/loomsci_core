# opencode adapter

Use this when running `{{HANDLE}}` inside opencode.

- Start the session in the project root.
- Read the project (README, AGENTS/CLAUDE, build files) before acting.
- Load the canonical instructions for `{{HANDLE}}`.
- Use `{{CLI}}` for the local bus; keep model calls inside the IDE.
- Register presence with:

```text
{{CLI}} presence --tool opencode --workspace <project> --as {{HANDLE}}
```

- If the default model stalls or the turn exceeds a reasonable time, report
  it and retry with a faster model (for example `--model deepseek/deepseek-flash`)
  or a smaller command; do not silently loop.
- You may create project-local helpers under `.loomsci/` or a temp directory;
  do not copy launchers/binaries into the project.
- Do not add credentials or absolute user-home paths to the workspace.
