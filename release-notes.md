# loomsci_core 0.1.0-beta.3 · Public Beta

- Version: `0.1.0-beta.3`
- Package: `releases/loomsci_core-0.1.0-beta.3.zip`
- SHA256: `d4299bd0e9d72f865007616e14e34ada252727254ce1640532dc77bb3c769ff2`

## Fix

- Ordered lists with blank lines between items now render as one `<ol>` and keep
  numbering. The previous parser treated each blank line as a list boundary.
- Fixed in ui-shell, collab, and notify (BUG-0002).

## Base

This hotfix carries the beta.2 post model: one Markdown body, no title field,
800-character full-post threshold, 300–500 character summaries, and local
fallback when DeepSeek is not configured.
