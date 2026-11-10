"""Optional OCR / speech-to-text adapters for media v0.2b.

Both are optional imports. Missing tools must surface as not_available, never
as fabricated output.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any


def _available(module: str) -> bool:
    return importlib.util.find_spec(module) is not None


def capabilities() -> dict[str, Any]:
    return {
        "ffmpeg": bool(shutil.which("ffmpeg")),
        "rapidocr": _available("rapidocr_onnxruntime"),
        "faster_whisper": _available("faster_whisper"),
        "whisper_model": os.environ.get("MEDIA_WHISPER_MODEL", "small"),
    }


def _suffix(content_type: str) -> str:
    value = str(content_type or "").lower()
    if value == "image/png":
        return ".png"
    if value in ("image/jpeg", "image/jpg"):
        return ".jpg"
    if value == "image/webp":
        return ".webp"
    if value.startswith("video/"):
        return ".mp4"
    if value.startswith("audio/"):
        return ".mp3"
    return ".bin"


def _to_wav(source: Path, target: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg_not_available")
    subprocess.run([
        ffmpeg, "-y", "-loglevel", "error", "-i", str(source),
        "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(target),
    ], check=True, timeout=120)


def ocr_bytes(data: bytes, content_type: str) -> dict[str, Any]:
    if not _available("rapidocr_onnxruntime"):
        raise RuntimeError("rapidocr_not_available")
    from rapidocr_onnxruntime import RapidOCR

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / ("input" + _suffix(content_type))
        path.write_bytes(data)
        engine = RapidOCR()
        result, _elapsed = engine(str(path))
    lines = []
    for item in result or []:
        if len(item) >= 2:
            lines.append(str(item[1]))
    return {"text": "\n".join(lines), "lines": len(lines), "engine": "rapidocr"}


def transcribe_bytes(data: bytes, content_type: str) -> dict[str, Any]:
    if not _available("faster_whisper"):
        raise RuntimeError("faster_whisper_not_available")
    from faster_whisper import WhisperModel

    model_name = os.environ.get("MEDIA_WHISPER_MODEL", "small")
    with tempfile.TemporaryDirectory() as tmp:
        source = Path(tmp) / ("input" + _suffix(content_type))
        source.write_bytes(data)
        wav = Path(tmp) / "input.wav"
        _to_wav(source, wav)
        model = WhisperModel(
            model_name,
            device="cpu",
            compute_type="int8",
            local_files_only=True,
        )
        segments, info = model.transcribe(str(wav), beam_size=5)
        items = [
            {"start": round(seg.start, 2), "end": round(seg.end, 2), "text": seg.text.strip()}
            for seg in segments
        ]
    return {
        "text": " ".join(item["text"] for item in items).strip(),
        "segments": items,
        "language": getattr(info, "language", None),
        "engine": "faster-whisper",
        "model": model_name,
    }
