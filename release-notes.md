# loomsci_core 0.1.0-beta.7 · Public Beta

- Version: `0.1.0-beta.7`
- Package: `releases/loomsci_core-0.1.0-beta.7.zip`
- SHA256: `1578f840edc7d0864f71a18e52a25e7a60df2818aaf57b610d0cd71bfeb43bcb`

## Login service

- `loomsci service install/uninstall/status`.
- macOS LaunchAgent runs `loomsci up --detach` at login.
- Windows current-user Startup folder runs the same command through a wrapper.
- No silent resident daemon; Core keeps the detached runtime state.

This release carries beta.6 DeepSeek settings, beta.5 runtime control, beta.4
`/app` routes, and the beta.2 post model.
