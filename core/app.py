"""Minimal local HTTP app for the S1 Core slice."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from flask import Flask, g, jsonify, request

from core import storage
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
