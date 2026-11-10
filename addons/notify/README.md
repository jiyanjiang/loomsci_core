# notify

Unread/digest add-on over Core inbox and tasks.

- no local database;
- reads `/v1/inbox`, `/v1/tasks`, `/v1/posts`;
- mark-all-read posts to `/v1/inbox/read`;
- optional desktop notification is best-effort and diagnostic only.

Run:

```bash
python -m addons.notify.server --home ~/.loomsci --port 8793
```

Open `http://127.0.0.1:8793/`.
