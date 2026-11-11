# loomsci_core · Public Beta

[中文](README.zh-CN.md) · [Docs](docs/en/quickstart.md) · [Backup](docs/en/backup.md) · [Migration](docs/en/migration.md) · [Release notes](release-notes.md) · [Security](SECURITY.md)

**A local-first research workspace for people who work with AI IDEs.**

LoomSci keeps the durable parts of your work — notes, posts, tasks, facts,
attachments, and agent instructions — on your computer. Your AI IDE is the
execution layer; LoomSci is the memory, audit trail, and portable asset layer.

> **Status: `0.1.0-beta.4` public beta.** Local-only, one owner, no login, no
> required cloud dependency. Not a production or multi-user server.

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
shasum -a 256 loomsci_core-0.1.0-beta.4.zip
# compare with release-manifest.json / SHA256SUMS
```

## Feedback

Open an issue with the version, OS, IDE, command, and redacted logs. Do not post
API keys, tokens, private keys, or personal data. Security reports: see
[SECURITY.md](SECURITY.md).

## License

Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
