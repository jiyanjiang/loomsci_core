# media

v0.1 media library add-on.

- indexes Core post attachments by reading `/v1/posts`;
- classifies image/audio/video/file;
- serves previews through `/api/attachment/<id>`;
- no transcoding, OCR, or transcription yet;
- no local database and no Core table/API changes.

Run:

```bash
python -m addons.media.server --home ~/.loomsci --port 8794
```

Open `http://127.0.0.1:8794/`.
