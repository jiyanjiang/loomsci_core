# Release evidence: v0.2.0-rc.8

Status: single-host private beta candidate. Not a public stable/1.0 release.

- code/tag: `v0.2.0-rc.8` -> `5777efe`
- package: `loomsci_core-0.2.0-rc.8.zip`
- SHA256: `929e847a5286b307cb890a50a3627acff92ee23b35116fc5e5a773908bc48dc4`
- tests: `18/18`
- single host: macOS 26.2, Python 3.12.13
- app origins: `app-<slug>.localhost:<core-port>`; Core `/apps` redirects 307
- app origin cookie/localStorage: empty; `/v1/items` with credentials 401
- update install: cross-process lock; duplicate apply rejected
- full view: left aligned, 16px gutter
- Windows dual-host: deferred by owner
- public stable: not declared
