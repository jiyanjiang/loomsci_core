# LoomSci Core 0.2.0-rc.4 — TAA-style item preview

Status: pre-release candidate. Not a public-beta declaration.

## Changes

- Item click opens a compact preview in the right rail; the center list does
  not move and keeps its scroll position.
- Preview toolbar: **Open full**, **Back to list**, **Delete**.
- Full mode expands the item into the center, hides the list and right rail,
  and starts at the top.
- Full-mode **← Back** returns to the preview and restores the list scroll
  position. Browser Back follows the same state.
- **Back to list** clears the preview and restores the list position.
- Selected list items are highlighted.
- Below 980px, item click opens full width; **← Back** returns to the list.

## Gates

- [ ] source checks and full unit tests
- [ ] macOS real-browser preview/full/back regression
- [ ] Windows fresh-venv tests and UI acceptance
- [ ] release package SHA256
- [ ] tag and push (only if requested)
