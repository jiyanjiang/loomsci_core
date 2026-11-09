# Quickstart (preview)

> Status: preview seed. There is no runnable host or installer yet.

## Prerequisites

- Python 3.12 on macOS or Windows.
- A local AI IDE (Codex, Pi, opencode, CodeBuddy, …) is optional at this stage.

## macOS

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Windows (PowerShell)

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

`requirements.txt` is intentionally empty in the preview seed.

## Planned first run (not implemented)

```text
loomsci init          # choose owner name and the default agent (alice)
loomsci serve         # loopback only, default port 8787
loomsci open          # open the local web UI
```

Planned local data home:

```text
macOS:   ~/.loomsci
Windows: %USERPROFILE%\.loomsci
```

The host will bind `127.0.0.1` by default. There is no login, no central
server, and no required TLS certificate.

## What “done” will mean

- Install to first message in about five minutes.
- One owner and one main agent by default.
- Data can be exported as JSON + Markdown and imported on another machine.
