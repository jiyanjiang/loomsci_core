# loomsci_core 0.1.0-beta.5 · Public Beta

- Version: `0.1.0-beta.5`
- Package: `releases/loomsci_core-0.1.0-beta.5.zip`
- SHA256: `ca37701ee72562c65ff3e7d2746e796479bf42fcbe5e6e97b04de76c1c97ef02`

## Runtime control

- `loomsci up --detach` starts Core in the background and survives terminal close.
- `loomsci status` reports PID, port, health, version, and primary URL.
- `loomsci down` stops only the recorded Core process.
- `loomsci open` opens ui-shell when running, otherwise Core `/app`.
- Runtime state is under `~/.loomsci/runtime/`.

This release carries the beta.2 post model, beta.3 loose-list fix, and beta.4
`/app` routes.
