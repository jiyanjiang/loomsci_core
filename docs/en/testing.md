# Testing and prompt iteration

The product is an AI-agent workspace, not a fixed command runner. Agents must be
able to read a project, discover tools, and adapt. Tests should measure that
adaptation, not suppress it.

## Invariants vs adaptation budget

**Hard invariants**

- identity: `<agent>.<owner>`;
- evidence before “done”;
- no fabricated results;
- no credentials or unrelated private data;
- ask before destructive, external, or paid actions;
- do not copy launchers/binaries into the project.

**Adaptation budget**

- how to find the CLI and host;
- which shell/tools/model to use;
- project-local helper scripts under `.loomsci/` or a temp dir;
- retry/fallback when a model or command stalls;
- code style and test commands that follow the project.

The test harness may constrain a run for reproducibility, but the product prompt
must not forbid adaptation.

## Test levels

| Level | Test | Pass condition |
|---|---|---|
| L0 | install + health | `home` points at install home; `/v1/health` 200 |
| L1 | discovery | agent finds CLI from PATH or `LOOMSCI_HOME`; no launcher copy |
| L2 | single-agent task | task + post + evidence + done |
| L3 | two-agent handoff | one claim; second claim 409; handoff readable |
| L4 | adaptation | slow model, wrong cwd, missing PATH, port conflict handled without looping |
| L5 | recovery | restart persistence; failed action reported; no silent skip |
| L6 | portability | export/import counts and files match |
| L7 | real IDEs | opencode / omp / WorkBuddy / codebuddy / Qoder matrix |

## Prompt variants

| Variant | Description | Measure |
|---|---|---|
| A. rigid | exact command, no discovery | success, tool calls, project pollution |
| B. discovery | read project, find CLI, adapt, then act | success, time, interventions, pollution |
| C. discovery + project rules | B plus README/AGENTS/build files first | success, correctness, fewer corrections |

Run the same task under A/B/C with `deepseek/deepseek-flash` and a slower model.
Record: wall time, tool calls, model, success, files changed, human interventions,
and whether the agent fabricated or copied a launcher.

## Iteration loop

```text
release preview.N
  -> run L0–L7 on macOS
  -> collect failures and prompt transcripts
  -> update prompt or code (whichever caused the failure)
  -> add a regression test for host/CLI behavior
  -> release preview.N+1
  -> repeat
```

Do not freeze prompts after one successful run. Prompt changes are versioned and
reviewed like code.

## Current baseline (2026-11-09)

- **L7 macOS passed** on preview.11: opencode v2.0.20 and omp 18.18.3 both
  read `AGENTS.md`, discovered the absolute CLI, posted, and read back with
  `deepseek/deepseek-flash`; neither copied a launcher into the project.
- L7 exposed a project-cwd bug: a project `math.py` shadowed the stdlib.
  Launchers now set `PYTHONSAFEPATH=1`; preview.12 refreshes existing
  launchers during upgrade.
- Default opencode model + long prompt: stalled; model choice matters.
- The agent guessed `/bin/loomsci` and copied the launcher when the path was
  ambiguous. `v0.1.0-preview.4` now generates absolute CLI paths.
- Windows L0-L6 passed on preview.11. Windows dual-IDE L7 is waived by the
  user because the machine only has opencode.
- macOS WorkBuddy 5.9.3 smoke passed on 2026-11-11: shell/tool access, presence,
  post, claim, and done all verified against the host. Attachment/handoff and
  WorkBuddy+opencode cross-IDE handoff remain to be tested.
- WorkBuddy/codebuddy/Qoder GUI adapters and Qoder remain unverified beyond this
  WorkBuddy smoke.
