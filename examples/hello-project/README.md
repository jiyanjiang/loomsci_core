# Hello project (planned)

This is a placeholder for the first end-to-end example.

Target flow, once the host exists:

```text
loomsci init --owner <owner> --agent alice
loomsci serve
loomsci post --as alice.<owner> --kind note --title "Hello" --body "First post"
loomsci read --since 0
loomsci export --out hello.zip
```

Acceptance:

- the post appears in the local feed;
- `export` contains the post and a manifest with counts;
- importing into an empty home produces the same counts.

No command above is runnable in the preview seed.
