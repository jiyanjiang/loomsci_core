# Tag design baseline

The TAA live database was inspected read-only as the design baseline:

```text
posts:            583
tagged posts:     549
distinct tags:    609
singleton tags:   392  (64%)
```

This confirms that free-form tags alone are not sufficient. The first tag cloud
must show only repeated tags, while singletons remain available for filtering
and later merging.

LoomSci starts with 48 posts, 0 tags, and 0 tag rows. Existing posts can be
backfilled after the tag contract is stable.

## Rules

- Normalize to lowercase, strip `#`, collapse whitespace, cap at 40 chars.
- Max 8 tags per post.
- `source = human | ai | import`; human tags win.
- Tag cloud shows repeated tags first; singleton tags are not displayed by default.
- Tag aliases are merged into one canonical tag.
- Do not use the tag cloud as a replacement for full-text search.
