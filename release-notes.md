# loomsci_core 0.1.0-beta.1 · Public Beta

- Version: `0.1.0-beta.1`
- Package: `releases/loomsci_core-0.1.0-beta.1.zip`
- SHA256: `8b753c7e0bceac75aa379b40569446c5d9638b7d77d0ccb71c891bdde5c5a04f`
- Installer: `install.sh --from-release` / `install.ps1 -FromRelease`
- Scope: local-only, single owner, no runtime sync/social.

## Included

- Core host and CLI
- ui-shell with i18n and site configuration
- media thumbnails/OCR/transcription (optional dependencies)
- research sources/facts/DeepSeek
- notify
- collab (optional profile)
- backup/verify/restore, offline migration, pre-upgrade backup

## Verified

- macOS and Windows clean-install sandboxes
- upgrade with automatic pre-upgrade backup
- WorkBuddy 5.9.3 macOS smoke
- opencode / omp L7 history
- SHA256 manifest installation

## Known limits

- No real-time two-way sync, social, or multi-user access.
- Windows WorkBuddy GUI and the full attachment/handoff matrix are not covered.
- Packages are not code-signed or notarized; OS security prompts may appear.
- media OCR/transcription require optional Python packages and ffmpeg.
