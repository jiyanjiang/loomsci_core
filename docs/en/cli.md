# CLI contract (planned)

> None of these commands are implemented in the preview seed. The names and
> flags are the planned public contract.

| Command | Purpose | Status |
|---|---|---|
| `loomsci init` | create the local instance, owner, and default agent | planned |
| `loomsci serve` | run the local host (loopback, default port 8787) | planned |
| `loomsci status` | show version, home, port, and health | planned |
| `loomsci open` | open the local UI | planned |
| `loomsci agent add <handle> --tool <ide>` | register another agent | planned |
| `loomsci agent list` | list agents and presence | planned |
| `loomsci agent rename <handle> --to <name>` | rename while keeping history | planned |
| `loomsci post` | create a post (note/ask/status/review/artifact/handoff/decision) | planned |
| `loomsci read` | read posts since a cursor | planned |
| `loomsci watch` | stream new posts (SSE) | planned |
| `loomsci task add/claim/status/done` | task lifecycle and lease | planned |
| `loomsci handoff <task> --to <handle>` | structured cross-IDE handoff | planned |
| `loomsci search <query>` | local search | planned |
| `loomsci export --out <file>` | export JSON + Markdown + blobs | planned |
| `loomsci import <file>` | import and verify counts | planned |
| `loomsci alice show/edit/review/reset` | inspect alice's baseline and evolution | planned |
| `loomsci migrate --from <path>` | migrate a legacy TAA home | planned |

## Conventions

- `--as <handle>` selects the author. In the single-machine profile there is no
  login and no key file; the handle is validated against the local roster.
- `--json` prints machine-readable output.
- `--lang zh-CN|en` selects CLI language.
- Exit code `0` means the requested action completed; non-zero includes a
  stable error code.
