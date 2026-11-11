# loomsci_core 0.1.0-beta.2 · Public Beta

- Version: `0.1.0-beta.2`
- Package: `releases/loomsci_core-0.1.0-beta.2.zip`
- SHA256: `473586b9316512d2d3927d4926885a761f879cecb29304606474819fceecd23a`
- Installer: `install.sh --from-release` / `install.ps1 -FromRelease`

## Changes

- Posts are one Markdown body; the separate title field is removed.
- Short posts (<= 800 characters) render in full in the feed.
- Long posts use a 300–500 character summary and link to the full post.
- With a DeepSeek key, summaries are generated asynchronously; without a key
  or on failure, a local extractive fallback is used.
- New feed/detail API: `/v1/posts?view=feed`, `/v1/posts/<id>`.
- Fixed ordered-list rendering in collab and notify (BUG-0001).

## Privacy

AI summaries send only long post bodies to the configured DeepSeek endpoint,
and only when `posts.summary.mode: ai` and a key is configured. Set
`posts.summary.mode: extractive` for fully local summaries.

## Known limits

- No real-time sync, social, or multi-user access.
- Windows WorkBuddy GUI is not in the tested matrix.
- No code signing or notarization.
