# SDK hello app

Minimal app using `loomsci_core.sdk.CoreClient`.

```text
POST /write
→ CoreClient.create_item()
→ Core /v1/items
```

Install through Core:

```bash
python -m loomsci_core --home /tmp/core app install ./examples/hello-app
```
