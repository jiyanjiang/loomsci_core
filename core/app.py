"""Minimal local HTTP app for the S1 Core slice."""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Mapping

from flask import Flask, Response, g, jsonify, request

from core import alice, handoff, storage
from core.home import HomeError, ensure_layout, resolve_home
from core.local_auth import check_request
from core.packs import Registry

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PORT = 8787


def _version() -> str:
    try:
        return (ROOT / "VERSION").read_text(encoding="utf-8").strip() or "0.0.0"
    except OSError:
        return "0.0.0"


def _storage_error(exc: Exception):
    if isinstance(exc, storage.NotFound):
        return jsonify({"ok": False, "error": "not_found"}), 404
    if isinstance(exc, storage.Conflict):
        return jsonify({"ok": False, "error": "conflict", "detail": str(exc)}), 409
    if isinstance(exc, storage.Forbidden):
        return jsonify({"ok": False, "error": "forbidden", "detail": str(exc)}), 403
    if isinstance(exc, ValueError):
        return jsonify({"ok": False, "error": "bad_request", "detail": str(exc)}), 400
    raise exc


def create_app(
    env: Mapping[str, str] | None = None,
    home: str | Path | None = None,
) -> Flask:
    resolution = resolve_home(explicit=home, env=env)
    if resolution.needs_migration:
        raise HomeError(
            f"legacy home detected at {resolution.path}; run `loomsci migrate` first"
        )
    layout = ensure_layout(resolution.path)
    storage.init_db(layout.db)

    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024
    app.config["LOOMSCI_HOME"] = str(layout.root)
    app.config["LOOMSCI_DB"] = str(layout.db)
    registry = Registry.from_env(env)
    app.extensions["loomsci_registry"] = registry
    app.extensions["loomsci_layout"] = layout

    def get_db():
        if "db" not in g:
            g.db = storage.connect(app.config["LOOMSCI_DB"])
        return g.db

    @app.teardown_appcontext
    def _close_db(_exc=None):
        conn = g.pop("db", None)
        if conn is not None:
            conn.close()

    @app.before_request
    def _local_gate():
        decision = check_request(
            method=request.method,
            path=request.path,
            host=request.host,
            origin=request.headers.get("Origin"),
            content_type=request.headers.get("Content-Type"),
            agent=request.headers.get("X-Loomsci-Agent"),
            registry=registry,
        )
        if not decision.ok:
            return jsonify(decision.payload or {"ok": False}), decision.status
        g.loomsci_agent = decision.agent
        return None

    @app.after_request
    def _headers(response):
        response.headers.setdefault("X-Loomsci-Protocol", "1.0")
        return response

    @app.get("/")
    @app.get("/app")
    def index():
        record = alice.read_agent(layout.root)
        agent_handle = escape(str((record or {}).get("handle") or "not initialized"))
        page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>loomsci_core</title>
<style>
:root {{ color-scheme: light dark; font-family: ui-sans-serif, system-ui, sans-serif; }}
body {{ max-width: 720px; margin: 8vh auto; padding: 0 24px; line-height: 1.55; }}
code, pre {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }}
pre {{ padding: 12px 14px; border: 1px solid color-mix(in srgb, currentColor 20%, transparent); border-radius: 8px; overflow: auto; }}
.muted {{ opacity: .7; }}
</style>
</head>
<body>
<h1>loomsci_core</h1>
<p>Local host is running. This is a status page, not a data view.</p>
<ul>
<li>profile: <code>{escape(registry.profile)}</code></li>
<li>routes: <code>{len(registry.routes())}</code></li>
<li>agent: <code>{agent_handle}</code></li>
</ul>
<p class="muted">CLI examples</p>
<pre>loomsci serve
loomsci post --as &lt;agent.owner&gt; --body "hello"
loomsci read --as &lt;agent.owner&gt;</pre>
<p><a href="/v1/meta/features">/v1/meta/features</a> · <a href="/v1/health">/v1/health</a></p>
</body>
</html>"""
        return Response(page, mimetype="text/html")

    @app.get("/v1/health")
    def health():
        return jsonify({
            "ok": True,
            "service": "loomsci_core",
            "version": _version(),
            "profile": registry.profile,
        })

    @app.get("/v1/version")
    def version():
        return jsonify({
            "ok": True,
            "product": "loomsci_core",
            "version": _version(),
            "profile": registry.profile,
            "protocol": "1.0",
        })

    @app.get("/v1/meta/features")
    def features():
        return jsonify({"ok": True, **registry.features()})

    @app.get("/v1/whoami")
    def whoami():
        return jsonify({"ok": True, "agent": g.loomsci_agent})

    @app.post("/v1/echo")
    def echo():
        payload = request.get_json(silent=True)
        if payload is None:
            return jsonify({"ok": False, "error": "json_required"}), 400
        return jsonify({"ok": True, "agent": g.loomsci_agent, "echo": payload})

    @app.get("/v1/posts")
    def posts_list():
        try:
            since = int(request.args.get("since", "0"))
            limit = int(request.args.get("limit", "50"))
        except ValueError:
            return jsonify({"ok": False, "error": "bad_pagination"}), 400
        posts = storage.list_posts(
            get_db(),
            since=since,
            limit=limit,
            thread_id=request.args.get("thread"),
        )
        return jsonify({"ok": True, "posts": posts})

    @app.post("/v1/posts")
    def posts_create():
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return jsonify({"ok": False, "error": "json_object_required"}), 400
        try:
            post = storage.create_post(
                get_db(),
                author=g.loomsci_agent,
                kind=str(body.get("kind") or "note"),
                title=str(body.get("title") or ""),
                body=str(body.get("body") or ""),
                thread_id=body.get("thread_id"),
                parent_id=body.get("parent_id"),
                meta=body.get("meta") if isinstance(body.get("meta"), dict) else {},
            )
        except Exception as exc:  # noqa: BLE001 - mapped below
            return _storage_error(exc)
        return jsonify({"ok": True, "post": post}), 201

    @app.get("/v1/tasks")
    def tasks_list():
        try:
            limit = int(request.args.get("limit", "50"))
        except ValueError:
            return jsonify({"ok": False, "error": "bad_pagination"}), 400
        tasks = storage.list_tasks(
            get_db(),
            status=request.args.get("status"),
            assigned_to=request.args.get("assigned_to"),
            limit=limit,
        )
        return jsonify({"ok": True, "tasks": tasks})

    @app.post("/v1/tasks")
    def tasks_create():
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return jsonify({"ok": False, "error": "json_object_required"}), 400
        try:
            task = storage.create_task(
                get_db(),
                title=str(body.get("title") or ""),
                description=str(body.get("description") or ""),
                acceptance=str(body.get("acceptance") or ""),
            )
        except Exception as exc:  # noqa: BLE001 - mapped below
            return _storage_error(exc)
        return jsonify({"ok": True, "task": task}), 201

    @app.post("/v1/tasks/<task_id>/claim")
    def tasks_claim(task_id: str):
        body = request.get_json(silent=True)
        if body is None:
            body = {}
        if not isinstance(body, dict):
            return jsonify({"ok": False, "error": "json_object_required"}), 400
        try:
            lease = int(body.get("lease_seconds", 3600))
            task = storage.claim_task(
                get_db(),
                task_id=task_id,
                agent=g.loomsci_agent,
                lease_seconds=lease,
            )
        except Exception as exc:  # noqa: BLE001 - mapped below
            return _storage_error(exc)
        return jsonify({"ok": True, "task": task})

    @app.post("/v1/tasks/<task_id>/done")
    def tasks_done(task_id: str):
        body = request.get_json(silent=True)
        if body is None:
            body = {}
        if not isinstance(body, dict):
            return jsonify({"ok": False, "error": "json_object_required"}), 400
        evidence = body.get("evidence")
        if not evidence:
            return jsonify({"ok": False, "error": "evidence_required"}), 400
        try:
            task = storage.done_task(
                get_db(),
                task_id=task_id,
                agent=g.loomsci_agent,
                evidence=evidence,
            )
        except Exception as exc:  # noqa: BLE001 - mapped below
            return _storage_error(exc)
        return jsonify({"ok": True, "task": task})

    @app.get("/v1/read")
    def read_get():
        scope = str(request.args.get("scope") or "posts")
        cursor = storage.get_read_cursor(
            get_db(), agent=g.loomsci_agent, scope=scope
        )
        return jsonify({"ok": True, "scope": scope, "cursor": cursor})

    @app.post("/v1/read")
    def read_set():
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return jsonify({"ok": False, "error": "json_object_required"}), 400
        try:
            last_seq = int(body.get("last_seq", 0))
        except (TypeError, ValueError):
            return jsonify({"ok": False, "error": "bad_last_seq"}), 400
        scope = str(body.get("scope") or "posts")
        storage.set_read_cursor(
            get_db(), agent=g.loomsci_agent, scope=scope, last_seq=last_seq
        )
        return jsonify({"ok": True, "scope": scope, "cursor": last_seq})

    @app.get("/v1/presence")
    def presence_list():
        agent = request.args.get("agent") or None
        return jsonify({
            "ok": True,
            "presence": storage.list_presence(get_db(), agent=agent),
        })

    @app.post("/v1/presence")
    def presence_set():
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return jsonify({"ok": False, "error": "json_object_required"}), 400
        tool = str(body.get("tool") or "").strip()
        workspace = str(body.get("workspace") or "").strip()
        if not tool or not workspace:
            return jsonify({"ok": False, "error": "tool_and_workspace_required"}), 400
        pid = body.get("pid")
        try:
            pid = int(pid) if pid is not None else None
        except (TypeError, ValueError):
            return jsonify({"ok": False, "error": "bad_pid"}), 400
        storage.upsert_presence(
            get_db(),
            agent=g.loomsci_agent,
            tool=tool,
            workspace=workspace,
            model=str(body.get("model") or ""),
            pid=pid,
        )
        return jsonify({
            "ok": True,
            "agent": g.loomsci_agent,
            "tool": tool,
            "workspace": workspace,
        })

    @app.post("/v1/handoff")
    def handoff_create():
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return jsonify({"ok": False, "error": "json_object_required"}), 400
        try:
            post = handoff.create(
                get_db(), author=g.loomsci_agent, payload=body
            )
        except Exception as exc:  # noqa: BLE001 - mapped below
            return _storage_error(exc)
        return jsonify({"ok": True, "post": post}), 201

    @app.errorhandler(404)
    def not_found(_error):
        return jsonify({"ok": False, "error": "not_found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(_error):
        return jsonify({"ok": False, "error": "method_not_allowed"}), 405

    @app.errorhandler(413)
    def too_large(_error):
        return jsonify({"ok": False, "error": "body_too_large"}), 413

    return app
