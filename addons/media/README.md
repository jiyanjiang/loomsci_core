# media

Media library add-on.

- v0.1: index/preview/play Core attachments
- v0.2a: ffmpeg image/video thumbnails
- v0.2b: optional OCR (RapidOCR) and speech transcription (faster-whisper)

Run:

```bash
python -m addons.media.server --home ~/.loomsci --port 8794
```

Optional tools:

```bash
pip install -r addons/media/requirements-media.txt
```

Pins matter: `onnxruntime==1.20.1` (1.27 fails to load its DLL on some Windows
hosts) and `ctranslate2==4.4.0` (4.8.5 access-violates on the Windows CPU
backend). Extractors run in a subprocess so native crashes cannot kill the
server.

If a tool is missing, the API returns `*_not_available`; it never fabricates
OCR/transcription output. OCR and transcription caches live under
`packs/media/data/`.
