# collab

Minimal collaboration add-on: rooms and room threads.

- room metadata is stored in `packs/collab/data/collab.db`;
- messages are Core posts with `thread_id=room:<room-id>`;
- Core tables and `/v1` shapes are unchanged;
- no E2EE, center, or sync.

Run:

```bash
python -m addons.collab.server --home ~/.loomsci --port 8792
```

Open `http://127.0.0.1:8792/`.
