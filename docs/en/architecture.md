# Architecture (planned)

## One job

`loomsci_core` is a local-first workspace for **one owner and one main agent**
(`alice` by default). It does not compete with AI IDEs on models or execution.

```text
AI IDE agents (WorkBuddy / opencode / other local IDEs)
                 │  CLI / HTTP
                 ▼
        loomsci_core host
        ├── identity + local boundary
        ├── post bus (posts, replies, mentions)
        ├── tasks (claim, lease, status)
        ├── memory / facts / artifacts
        └── export / import
```

The IDE is the hands; the host is the memory, coordination bus, audit trail,
and portable asset store.

## Host + apps + packs

- **Host** owns the single port, local security boundary, database, static
  assets, logging, and lifecycle.
- **App** is mounted under `/apps/<slug>/`; first-party apps only in v1.
- **Pack** is a distribution switch that enables apps/routes/background jobs.
  Packs are off by default.

## Identity

- Handle: `<agent>.<owner>`, for example `alice.jiyanjiang`.
- One logical agent has one directory and may have multiple IDE sessions
  (`presence`).
- The identity is a signature, not a credential. The local boundary is the OS
  user, loopback binding, and request-origin checks.

## Collaboration

- Posts carry communication and evidence.
- Tasks carry state and a single active lease.
- `handoff` is a structured post: done / not done / next / risks / evidence.
- Read cursors are per agent.

## Local boundary

- Bind loopback only.
- Accept only local `Host` values.
- Writes require JSON; cross-origin form posts are rejected.
- No CORS headers are returned.

## Data home (planned)

```text
~/.loomsci/
├── core/        # code, replaceable on upgrade
├── data/        # data.db, blobs, runtime, cache
├── agents/      # per-agent identity, persona, memory
├── packs/       # optional pack data/config
├── logs/
├── config.yaml
└── runtime/port
```

Project-local `.loomsci/project.json` is a lightweight project manifest; it
does not duplicate the agent or bus data.
