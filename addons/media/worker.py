"""Isolated OCR/transcription worker.

Running extractors in a separate process keeps cv2/av/ctranslate2 failures from
killing the HTTP server.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from . import extract


def main() -> int:
    if len(sys.argv) != 4:
        print(json.dumps({"ok": False, "error": "usage: worker kind path content_type"}))
        return 2
    kind, source, content_type = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
    data = source.read_bytes()
    try:
        result = extract.ocr_bytes(data, content_type) if kind == "ocr" else extract.transcribe_bytes(data, content_type)
    except Exception as exc:  # noqa: BLE001 - isolated boundary
        print(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"}))
        return 1
    print(json.dumps({"ok": True, **result}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
