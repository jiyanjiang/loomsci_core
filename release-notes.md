# loomsci_core 0.1.0-beta.4 · Public Beta

- Version: `0.1.0-beta.4`
- Package: `releases/loomsci_core-0.1.0-beta.4.zip`
- SHA256: `90da02e63c8a24337550bb5f1fd98b91fdb14cc96a006e8fa4fadeb1adba95c1`

## Fix

- ui-shell now serves `/app`, `/app/posts`, `/app/tasks`, `/app/memory`,
  `/app/inbox`, and `/app/site` instead of returning 404.
- Navigation updates the URL; browser back/forward restores the active view.
- Post detail (`/app/posts?post=<id>`) is unchanged.

This hotfix carries the beta.2 post model and beta.3 loose-list fix.
