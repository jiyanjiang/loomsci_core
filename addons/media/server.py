"""Minimal media library add-on v0.1.

Indexes Core post attachments (images/audio/video/files) and serves a local
preview. No transcoding, OCR, or transcription yet. Core tables/API unchanged.
"""

from __future__ import annotations

import argparse
import http.client
import json
import mimetypes
import os
import shutil
import subprocess
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"


def default_agent(home: Path | None = None) -> str:
    candidates = []
    if home:
        candidates.append(home)
    env_home = os.environ.get("LOOMSCI_HOME")
    if env_home:
        candidates.append(Path(env_home).expanduser())
    candidates.extend([Path.home() / ".loomsci", ROOT.parents[2]])
    for base in candidates:
        path = base / "agents" / "alice" / "agent.json"
        if path.is_file():
            try:
                return str(json.loads(path.read_text(encoding="utf-8"))["handle"])
            except (OSError, ValueError, KeyError):
                pass
    return "alice.owner"


def kind(content_type: str) -> str:
    value = str(content_type or "").lower()
    if value.startswith("image/"):
        return "image"
    if value.startswith("audio/"):
        return "audio"
    if value.startswith("video/"):
        return "video"
    return "file"


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    upstream = "127.0.0.1"
    upstream_port = 8787
    agent = "alice.owner"
    thumb_dir = Path("thumbs")

    def do_GET(self) -> None:
        self._route()

    def _route(self) -> None:
        path = urlsplit(self.path).path
        if path == "/api/capabilities":
            return self._json(200, {"ok": True, "ffmpeg": bool(shutil.which("ffmpeg")),
                                    "tesseract": bool(shutil.which("tesseract")),
                                    "whisper": bool(shutil.which("whisper"))})
        if path == "/api/library":
            return self._library()
        if path.startswith("/api/thumbnail/"):
            return self._thumbnail(unquote(path[len("/api/thumbnail/"):]))
        if path.startswith("/api/attachment/"):
            return self._attachment(unquote(path[len("/api/attachment/"):]))
        self._static(path)

    def _json(self, status: int, payload: dict) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _core_json(self, path: str) -> tuple[int, dict]:
        status, headers, data = self._core_bytes(path)
        try:
            return status, json.loads(data or b"{}")
        except ValueError:
            return status, {"ok": False, "error": "invalid core response"}

    def _core_bytes(self, path: str) -> tuple[int, dict, bytes]:
        try:
            conn = http.client.HTTPConnection(self.upstream, self.upstream_port, timeout=20)
            conn.request("GET", path, headers={"X-Loomsci-Agent": self.agent})
            response = conn.getresponse()
            data = response.read()
            headers = dict(response.getheaders())
            conn.close()
            return response.status, headers, data
        except Exception as exc:  # noqa: BLE001 - add-on boundary
            return 502, {}, json.dumps({"ok": False, "error": f"core proxy: {exc}"}).encode()

    def _library(self) -> None:
        status, status_payload = self._core_json("/v1/status")
        if status != 200:
            return self._json(502, {"ok": False, "error": "core_unreachable"})
        last_seq = int(status_payload.get("last_seq") or 0)
        items: dict[str, dict] = {}
        since = 0
        while since < last_seq:
            code, payload = self._core_json(f"/v1/posts?since={since}&limit=200")
            if code != 200:
                return self._json(502, {"ok": False, "error": "core_unreachable"})
            posts = payload.get("posts") or []
            if not posts:
                break
            for post in posts:
                since = max(since, int(post.get("seq") or 0))
                for attachment in post.get("attachments") or []:
                    item = dict(attachment)
                    item["kind"] = kind(item.get("content_type", ""))
                    item["post_id"] = post.get("id")
                    item["author"] = post.get("author")
                    item["created_at"] = post.get("created_at")
                    if item["kind"] in ("image", "video"):
                        item["thumbnail"] = f"/api/thumbnail/{item['id']}"
                    items[str(item.get("id"))] = item
        values = sorted(items.values(), key=lambda item: str(item.get("created_at") or ""), reverse=True)
        counts = {name: 0 for name in ("image", "audio", "video", "file")}
        for item in values:
            counts[item["kind"]] += 1
        self._json(200, {"ok": True, "counts": counts, "items": values[:500]})

    def _thumbnail(self, attachment_id: str) -> None:
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            return self._json(501, {"ok": False, "error": "ffmpeg_unavailable"})
        status, headers, data = self._core_bytes(f"/v1/attachments/{attachment_id}")
        if status != 200:
            return self._json(404, {"ok": False, "error": "attachment_not_found"})
        content_type = headers.get("Content-Type", "")
        if not (content_type.startswith("image/") or content_type.startswith("video/")):
            return self._json(415, {"ok": False, "error": "not_visual"})
        self.thumb_dir.mkdir(parents=True, exist_ok=True)
        target = self.thumb_dir / f"{attachment_id}.jpg"
        if not target.is_file():
            suffix = ".png" if content_type.startswith("image/") else ".mp4"
            with tempfile.NamedTemporaryFile(dir=self.thumb_dir, suffix=suffix, delete=False) as fh:
                fh.write(data)
                source = Path(fh.name)
            try:
                args = [ffmpeg, "-y", "-loglevel", "error", "-i", str(source)]
                if content_type.startswith("video/"):
                    args += ["-ss", "1"]
                args += ["-frames:v", "1", "-vf", "scale=320:-2", str(target)]
                subprocess.run(args, check=True, timeout=30,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except (OSError, subprocess.SubprocessError):
                return self._json(422, {"ok": False, "error": "thumbnail_failed"})
            finally:
                source.unlink(missing_ok=True)
        if not target.is_file():
            return self._json(422, {"ok": False, "error": "thumbnail_failed"})
        payload = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "image/jpeg")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "public, max-age=86400")
        self.end_headers()
        self.wfile.write(payload)

    def _attachment(self, attachment_id: str) -> None:
        status, headers, data = self._core_bytes(f"/v1/attachments/{attachment_id}")
        if status != 200:
            return self._json(status, {"ok": False, "error": "attachment_not_found"})
        self.send_response(200)
        self.send_header("Content-Type", headers.get("Content-Type", "application/octet-stream"))
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _static(self, path: str) -> None:
        if path in ("", "/"):
            path = "/index.html"
        target = (WEB / path.lstrip("/")).resolve()
        if WEB.resolve() not in target.parents and target != WEB.resolve():
            return self.send_error(404)
        if not target.is_file():
            return self.send_error(404)
        data = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mimetypes.guess_type(str(target))[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt: str, *args) -> None:
        print("[media] " + fmt % args, flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8794)
    parser.add_argument("--home")
    parser.add_argument("--upstream", default="127.0.0.1")
    parser.add_argument("--upstream-port", type=int, default=8787)
    parser.add_argument("--agent")
    args = parser.parse_args()
    home = Path(args.home).expanduser() if args.home else None
    Handler.upstream = args.upstream
    Handler.upstream_port = args.upstream_port
    Handler.agent = args.agent or default_agent(home)
    base = home or Path.home() / ".loomsci"
    Handler.thumb_dir = base / "packs" / "media" / "data" / "thumbs"
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"media on http://127.0.0.1:{args.port} (agent={Handler.agent})", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
