# SDK hello app

Minimal app using `loomsci_core.sdk.CoreClient`.

```text
POST /write
→ CoreClient.create_item()
→ Core /v1/items
```

Install through the Core API (the preview has no app CLI yet):

```bash
curl -sS -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"source":"/absolute/path/to/examples/hello-app"}' \
  http://127.0.0.1:8795/v1/apps/install
```
