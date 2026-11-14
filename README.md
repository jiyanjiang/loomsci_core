# loomsci_core · Public Beta

[中文](README.zh-CN.md) · [Docs](docs/en/quickstart.md) · [Core v0 guide](docs/en/core-v0/platform.md) · [API](docs/en/core-v0/core-api.md) · [App developer](docs/en/core-v0/app-developer.md) · [Core cutoff](docs/en/core-cutoff.md) · [Core contract](docs/en/core-contract.md) · [App manifest](docs/en/app-manifest.md) · [Report spec](docs/en/report-app.md) · [Distribution](docs/en/distribution.md) · [Signing/trust](docs/en/signing-trust.md) · [Platform matrix](docs/en/platform-test-matrix.md) · [IDE matrix](docs/en/ide-compatibility.md) · [Backup](docs/en/backup.md) · [Migration](docs/en/migration.md) · [Release notes](release-notes.md) · [Security](SECURITY.md)

**A local-first research workspace for people who work with AI IDEs.**

LoomSci keeps the durable parts of your work — notes, posts, tasks, facts,
attachments, and agent instructions — on your computer. Your AI IDE is the
execution layer; LoomSci is the memory, audit trail, and portable asset layer.

> **Status: `0.1.0-beta.28` public beta.** Local-only, one owner, no login, no
> required cloud dependency. Not a production or multi-user server.
>
> **Product direction (draft):** LoomSci Core is becoming a minimal, stable
> local app runtime distributed as **Core + Specific APP**. The current beta is
> the legacy implementation; see the [Core contract](docs/en/core-contract.md),
> [App manifest](docs/en/app-manifest.md), and
> [distribution model](docs/en/distribution.md).

## Requirements

- Python **3.12**
- One AI IDE that can run terminal commands:
  **WorkBuddy**, **opencode**, or **omp**
- macOS or Windows

WorkBuddy 5.9.3 has been smoke-tested on macOS. opencode and omp have real L7
history. The Windows WorkBuddy GUI has not yet been tested.

## Install

macOS / Linux:

```bash
curl -fsSL https://raw.githubusercontent.com/jiyanjiang/loomsci_core/main/install.sh \
  -o /tmp/loomsci-install.sh
bash /tmp/loomsci-install.sh --from-release --dry-run
bash /tmp/loomsci-install.sh --from-release
~/.loomsci/bin/loomsci setup
~/.loomsci/bin/loomsci up
```

Windows PowerShell:

```powershell
Invoke-WebRequest -UseBasicParsing `
  https://raw.githubusercontent.com/jiyanjiang/loomsci_core/main/install.ps1 `
  -OutFile $env:TEMP\loomsci-install.ps1
powershell -ExecutionPolicy Bypass -File $env:TEMP\loomsci-install.ps1 -FromRelease -DryRun
powershell -ExecutionPolicy Bypass -File $env:TEMP\loomsci-install.ps1 -FromRelease
& "$env:USERPROFILE\.loomsci\bin\loomsci.cmd" setup
& "$env:USERPROFILE\.loomsci\bin\loomsci.cmd" up
```

The installer reads `release-manifest.json`, downloads the package, and verifies
its SHA-256 before installing. A mismatch aborts.

## First run

`loomsci setup` asks for owner, agent handle, detected IDE, add-on profile, and an
optional DeepSeek key. The key is stored only in `~/.loomsci/config.yaml` with
mode `0600`; it is never written into the project or logs.

Then open:

- Core UI: `http://127.0.0.1:8787/app`
- ui-shell (if installed): `http://127.0.0.1:8790/`

## Start, stop, and status

Run Core in the background:

```bash
~/.loomsci/bin/loomsci up --detach
~/.loomsci/bin/loomsci status
~/.loomsci/bin/loomsci open       # open the primary UI URL
~/.loomsci/bin/loomsci down
~/.loomsci/bin/loomsci service install
~/.loomsci/bin/loomsci service status
~/.loomsci/bin/loomsci service uninstall
```

`service install` adds a login item that runs `up --detach` at login. It does
not silently install a resident daemon; Core still uses the same detached
runtime state.

`up --detach` keeps Core alive after the terminal closes. `status` reports the
PID, port, health, version, and primary URL. `open` prefers the ui-shell URL
when that add-on is running, otherwise it opens the Core `/app` fallback.
`down` stops only the detached Core process recorded in the runtime state.

## Updates

Settings → Updates checks the beta channel, downloads a release, verifies its
SHA-256, and can install with backup and restart. Automatic installation is not
enabled; the user confirms installation.

```bash
~/.loomsci/bin/loomsci update status
~/.loomsci/bin/loomsci update check
~/.loomsci/bin/loomsci update download
~/.loomsci/bin/loomsci update apply
```

## Search benchmark

```bash
python scripts/bench_search.py --posts 10000 --facts 50000
```

Search uses SQLite FTS5; the benchmark reports p50/p95 latency.

## Project scan

Read-only project discovery; it does not copy files or execute project code:

```bash
~/.loomsci/bin/loomsci project scan --root ~/Downloads --depth 3   --exclude 'share_loomsci_v*' --json
```

The scan records paths, marker files, counts, README excerpts, database files,
and app hints for review. Register it as a local reference without copying:

```bash
~/.loomsci/bin/loomsci project register --root <dir> \
  --code <code> --name <name> --source root=<dir> --app-port 5010
~/.loomsci/bin/loomsci project list
~/.loomsci/bin/loomsci project show <code>
~/.loomsci/bin/loomsci project refresh <code>
~/.loomsci/bin/loomsci project inspect <code>
~/.loomsci/bin/loomsci project review <code> --status selected \
  --completeness 4 --maturity 4 --commercial 3 --direction "research data"
~/.loomsci/bin/loomsci project app list <code>
~/.loomsci/bin/loomsci project app check <code>
~/.loomsci/bin/loomsci project evaluate <code> --status reviewed \
  --problem 4 --evidence 4 --implementation 4 --output 4 \
  --application 4 --commercial 4 --maintainability 4
~/.loomsci/bin/loomsci project template list
~/.loomsci/bin/loomsci project template create book \
  --target ~/book-project --code my-book --name "My Book"
```

New projects are `candidate`; only `selected` projects become active. Review
scores and notes are metadata; they do not copy project content.

Registered projects appear at `http://127.0.0.1:8790/app/projects`: sources,
file-type counts, monthly activity, databases, apps, and recent files. All views
are metadata-only; source files are never copied.

## Provider settings

Open `http://127.0.0.1:8790/app/settings` and enter a DeepSeek API key. The
primary form is one field; base URL and model use presets. The key is written
only to `~/.loomsci/config.yaml` with mode `0600`, is never returned by the API,
and is not included in backups or exports.

The same provider configuration is used by post summaries and the research
add-on. Settings → Advanced providers exposes Aliyun DashScope and Volcengine
Ark base URL, model, key, and connection test.

## Posts and summaries

Posts are one Markdown document. There is no separate title field: a heading
such as `# 第一个改进` is part of the body.

- Up to **800 characters**: the post is shown in full.
- Over **800 characters**: the UI shows a generated **300–500 character**
  summary and links to the full post.
- With a DeepSeek key, the summary is generated asynchronously.
- Without a key, or when the model fails, a deterministic local excerpt is
  shown instead; it is labelled as a fallback, not as an AI summary.

AI summaries send the long post body to the configured model provider. Set
`posts.summary.mode: extractive` in `~/.loomsci/config.yaml` to keep summaries
fully local. Short posts are never sent for summarization.

```yaml
posts:
  summary:
    mode: ai        # ai | extractive
    min_chars: 800
    max_chars: 500
```

## Add-ons

```bash
~/.loomsci/bin/loomsci addon list
~/.loomsci/bin/loomsci addon profile personal
~/.loomsci/bin/loomsci addon profile maker
~/.loomsci/bin/loomsci addon status
```

- `ui-shell` — Markdown UI, i18n, site config
- `media` — thumbnails, OCR, speech transcription (optional tools)
- `research` — sources, facts, DeepSeek-assisted work
- `notify` — unread digest
- `collab` — rooms, threads, handoff

## Your data stays yours

- Data lives in `~/.loomsci`: SQLite, agents, packs, attachments.
- `loomsci backup create` builds a portable bundle with DB, Markdown, and assets.
- `loomsci backup verify` checks hashes and SQLite integrity.
- `loomsci sync import` restores into an installed, empty workspace.
- Upgrades create `~/.loomsci/backups/pre-upgrade-<version>.zip` first and abort
  if that backup fails.
- API keys, tokens, and private keys are never included in asset backups.
- Downloaded reference documents can be explicitly marked `backup=reference`.

## AI IDE integration

After `loomsci setup`, the agent adapters are under:

```text
~/.loomsci/agents/<short>/adapters/
```

Use the absolute CLI path in the IDE prompt, for example:

```text
$HOME/.loomsci/bin/loomsci --url http://127.0.0.1:8787 --as alice.<owner>
```

If the IDE cannot execute shell commands, it should say so and provide exact
commands rather than claiming success.

## Security boundary

- Core binds loopback only (`127.0.0.1`), with one owner and no login.
- No required cloud service, no center, no multi-user access in this beta.
- AI summaries are the only optional model upload: only long post bodies, and
  only when a DeepSeek key is configured and `posts.summary.mode` is `ai`.
- No encryption at rest; use full-disk encryption and trusted transfer channels.
- Packages use a SHA-256 release manifest. They are **not** code-signed or
  notarized; macOS Gatekeeper / Windows SmartScreen may warn.
- Do not expose the Core port to a network.

## Beta limitations

- No real-time two-way sync or social features.
- WorkBuddy Windows and attachment/handoff flows are not yet part of the tested
  beta matrix.
- `media` OCR/transcription need optional Python packages and ffmpeg.
- The CLI is the setup surface; a guided UI is future work.

## Verify a release

```bash
shasum -a 256 loomsci_core-0.1.0-beta.28.zip
# compare with release-manifest.json / SHA256SUMS
```

## Feedback

Open an issue with the version, OS, IDE, command, and redacted logs. Do not post
API keys, tokens, private keys, or personal data. Security reports: see
[SECURITY.md](SECURITY.md).

## License

Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
