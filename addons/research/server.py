"""Minimal research v0.1 add-on: deterministic workspace/source/fact/gate.

No LLM calls. The IDE agent writes OUTLINE/DRAFT; this add-on stores evidence,
checks the gate, and can publish a gated draft to Core.
"""

from __future__ import annotations

import argparse
import http.client
import json
import mimetypes
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from . import llm, store

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


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    upstream = "127.0.0.1"
    upstream_port = 8787
    agent = "alice.owner"
    data_root = Path("research")
    home = Path.home() / ".loomsci"

    def do_GET(self) -> None:
        self._route("GET")

    def do_POST(self) -> None:
        self._route("POST")

    def _route(self, method: str) -> None:
        path = urlsplit(self.path).path
        if path == "/api/workspaces" and method == "GET":
            return self._json(200, {"ok": True, "workspaces": store.list_workspaces(self.data_root)})
        if path == "/api/workspaces" and method == "POST":
            return self._new()
        if path.startswith("/api/workspaces/"):
            rest = unquote(path[len("/api/workspaces/"):])
            ref, _, action = rest.partition("/")
            if not action and method == "GET":
                return self._describe(ref)
            if action == "sources" and method == "POST":
                return self._source(ref)
            if action == "facts" and method == "POST":
                return self._fact(ref)
            if action == "draft" and method == "POST":
                return self._draft(ref)
            if action == "check" and method == "POST":
                return self._check(ref)
            if action == "retrieve" and method == "POST":
                return self._retrieve(ref)
            if action == "ask" and method == "POST":
                return self._ask(ref)
            if action == "publish" and method == "POST":
                return self._publish(ref)
        self._static(path)

    def _json(self, status: int, payload: dict) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(raw.decode("utf-8"))
        except ValueError:
            return {}
        return data if isinstance(data, dict) else {}

    def _error(self, exc: Exception) -> None:
        self._json(400, {"ok": False, "error": str(exc)[:500]})

    def _new(self) -> None:
        body = self._read_json()
        try:
            item = store.new(str(body.get("prompt") or ""), root=self.data_root,
                             title=str(body.get("title") or ""))
        except Exception as exc:  # noqa: BLE001
            return self._error(exc)
        self._json(201, {"ok": True, **item})

    def _describe(self, ref: str) -> None:
        try:
            self._json(200, {"ok": True, **store.describe(self.data_root, ref)})
        except Exception as exc:  # noqa: BLE001
            self._json(404, {"ok": False, "error": str(exc)})

    def _source(self, ref: str) -> None:
        body = self._read_json()
        try:
            item = store.add_source(
                self.data_root, ref,
                url=str(body.get("url") or ""),
                title=str(body.get("title") or ""),
                text=str(body.get("text") or ""),
                grade=body.get("grade"),
            )
        except Exception as exc:  # noqa: BLE001
            return self._error(exc)
        self._json(201, {"ok": True, "source": item})

    def _fact(self, ref: str) -> None:
        body = self._read_json()
        try:
            item = store.add_fact(
                self.data_root, ref,
                claim=str(body.get("claim") or ""),
                url=str(body.get("url") or ""),
                quote=str(body.get("quote") or ""),
            )
        except Exception as exc:  # noqa: BLE001
            return self._error(exc)
        self._json(201, {"ok": True, "fact": item})

    def _draft(self, ref: str) -> None:
        body = self._read_json()
        try:
            result = store.write_draft(self.data_root, ref, str(body.get("draft") or ""))
        except Exception as exc:  # noqa: BLE001
            return self._error(exc)
        self._json(200, result)

    def _check(self, ref: str) -> None:
        try:
            result = store.check(self.data_root, ref)
        except Exception as exc:  # noqa: BLE001
            return self._error(exc)
        self._json(200 if result.get("ok") else 422, {"ok": True, "gate": result})

    def _retrieve(self, ref: str) -> None:
        body = self._read_json()
        try:
            key = llm.deepseek_key(self.home)
            if not key:
                return self._json(503, {"ok": False, "error": "deepseek_key_missing"})
            data = store.describe(self.data_root, ref)
            query = str(body.get("query") or data.get("prompt") or "")
            results = llm.search(query, key, limit=int(body.get("limit") or 8))
            added = []
            for item in results:
                added.append(store.add_source(self.data_root, ref, **item))
        except Exception as exc:  # noqa: BLE001
            return self._error(exc)
        self._json(200, {"ok": True, "added": added})

    def _ask(self, ref: str) -> None:
        body = self._read_json()
        try:
            key = llm.deepseek_key(self.home)
            if not key:
                return self._json(503, {"ok": False, "error": "deepseek_key_missing"})
            data = store.describe(self.data_root, ref)
            prompt = str(data.get("prompt") or "")
            sources = data.get("sources") or []
            if not sources and body.get("sources", True) is not False:
                results = llm.search(prompt, key, limit=int(body.get("source_limit") or 8))
                for item in results:
                    store.add_source(self.data_root, ref, **item)
                data = store.describe(self.data_root, ref)
                sources = data.get("sources") or []
            text = llm.answer(prompt, sources, key, model=str(body.get("model") or llm.MODEL))
            store.write_draft(self.data_root, ref, text)
            result = store.check(self.data_root, ref)
        except Exception as exc:  # noqa: BLE001
            return self._error(exc)
        self._json(200 if result.get("ok") else 422, {"ok": True, "draft": text, "gate": result})

    def _publish(self, ref: str) -> None:
        try:
            result = store.check(self.data_root, ref)
            if not result.get("ok"):
                return self._json(422, {"ok": False, "error": "gate_failed", "gate": result})
            data = store.describe(self.data_root, ref)
            body = f"# {data.get('title') or ref}\n\n{data.get('draft') or ''}\n\n## Sources\n" + "\n".join(
                f"- [{s.get('id')}] {s.get('title')} — {s.get('url')}" for s in data.get("sources") or []
            )
            status, payload = self._core("POST", "/v1/posts", {
                "kind": "artifact",
                "title": str(data.get("title") or ref),
                "body": body,
                "thread_id": f"research:{data.get('code')}",
                "meta": {"research": f"{data.get('code')}@{data.get('version')}", "gate": result},
            })
        except Exception as exc:  # noqa: BLE001
            return self._error(exc)
        self._json(status, payload)

    def _core(self, method: str, path: str, payload: dict | None = None) -> tuple[int, dict]:
        data = json.dumps(payload).encode() if payload is not None else None
        headers = {"X-Loomsci-Agent": self.agent}
        if data:
            headers["Content-Type"] = "application/json"
        try:
            conn = http.client.HTTPConnection(self.upstream, self.upstream_port, timeout=20)
            conn.request(method, path, body=data, headers=headers)
            response = conn.getresponse()
            raw = response.read()
            conn.close()
            return response.status, json.loads(raw or b"{}")
        except Exception as exc:  # noqa: BLE001 - add-on boundary
            return 502, {"ok": False, "error": f"core proxy: {exc}"}

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
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt: str, *args) -> None:
        print("[research] " + fmt % args, flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8795)
    parser.add_argument("--home")
    parser.add_argument("--upstream", default="127.0.0.1")
    parser.add_argument("--upstream-port", type=int, default=8787)
    parser.add_argument("--agent")
    args = parser.parse_args()
    home = Path(args.home).expanduser() if args.home else None
    base = home or Path.home() / ".loomsci"
    Handler.upstream = args.upstream
    Handler.upstream_port = args.upstream_port
    Handler.agent = args.agent or default_agent(home)
    Handler.data_root = base / "packs" / "research" / "data"
    Handler.home = base
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"research on http://127.0.0.1:{args.port} (agent={Handler.agent})", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
