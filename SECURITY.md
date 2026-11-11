# Security Policy

## Supported versions

`loomsci_core` is in preview. Security fixes are applied to the latest preview
and the default branch. Older snapshots may not receive fixes.

## Reporting a vulnerability

Please **do not** open a public issue for a security problem.

Use GitHub's private vulnerability reporting for this repository:

1. Open the repository's **Security** tab.
2. Choose **Report a vulnerability**.
3. Include affected version/commit, operating system, reproduction steps,
   impact, and any suggested fix.

If private reporting is unavailable, open a minimal public issue asking for a
private channel; do not include exploit details, credentials, personal data, or
internal addresses.

## Post summaries and model calls

Posts are stored locally. AI summaries are optional and are the only automatic
model upload in this beta:

- only posts longer than 800 characters are eligible;
- the long post body is sent to the configured DeepSeek endpoint;
- no upload occurs without a configured key and `posts.summary.mode: ai`;
- `posts.summary.mode: extractive` keeps summaries fully local;
- a failed call falls back to a local excerpt and records only a short error.

Do not put secrets in a post body if AI summaries are enabled.

## Scope

In scope:

- authentication/authorization boundaries of the local host;
- path traversal, symlink, archive, and file-permission issues;
- SSRF and local-network exposure;
- secret leakage in logs, exports, releases, or the public repository;
- update/install verification.

Out of scope:

- vulnerabilities in third-party AI IDEs or model providers;
- issues that require an already-compromised local OS account;
- social engineering.

## Disclosure

We will acknowledge a report, investigate, and coordinate a fix and disclosure
timeline with the reporter. Please give us reasonable time before public
disclosure.
