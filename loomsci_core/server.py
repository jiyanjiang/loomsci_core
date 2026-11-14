#!/usr/bin/env python3
"""Minimal Core v0 HTTP prototype.

Run: python3 prototype/core_v0/server.py --home /tmp/loomsci-core
Not product code. Exposes items, tags, blobs, search behind a local token.
"""

from __future__ import annotations

import argparse
import atexit
import base64
import binascii
import secrets
from pathlib import Path

from flask import Flask, Response, g, jsonify, request

from . import backup as backup_store
from .version import __version__
from . import store
from .app_host import AppHost, AppHostError


def create_app(home: Path, core_url: str = "http://127.0.0.1:8795") -> Flask:
    home = home.expanduser()
    (home / "data" / "blobs").mkdir(parents=True, exist_ok=True)
    db = home / "data" / "core.db"
    store.init_db(db)
    token_path = home / "local.token"
    if not token_path.is_file():
        token_path.write_text(secrets.token_hex(32) + "\n", encoding="utf-8")
        try:
            token_path.chmod(0o600)
        except OSError:
            pass
    token = token_path.read_text(encoding="utf-8").strip()
    app = Flask(__name__)
    app.config["TOKEN"] = token
    app.config["HOME"] = str(home)
    app.config["DB"] = str(db)
    app.config["BLOB_DIR"] = str(home / "data" / "blobs")
    host = AppHost(home, core_url)
    app.config["HOST"] = host
    atexit.register(lambda: [host.stop(slug) for slug in list(host.procs)])

    def db_conn():
        if "db" not in g:
            g.db = store.connect(Path(app.config["DB"]))
        return g.db

    @app.teardown_appcontext
    def close_db(_exc=None):
        conn = g.pop("db", None)
        if conn is not None:
            conn.close()

    @app.before_request
    def auth():
        if request.path in {"/v1/health", "/v1/version"}:
            return None
        header = request.headers.get("Authorization", "")
        supplied = header[7:].strip() if header.startswith("Bearer ") else request.headers.get("X-LoomSci-Token", "")
        if supplied and secrets.compare_digest(supplied, token):
            g.app_slug = None
            return None
        info = host.tokens.get(supplied or "")
        if info:
            g.app_slug = info["slug"]
            return None
        return jsonify({"ok": False, "error": "unauthorized"}), 401

    def allowed(app_name: str) -> bool:
        return getattr(g, "app_slug", None) in (None, app_name)

    @app.get("/v1/health")
    def health():
        return jsonify({"ok": True, "api": "core/1", "schema": 1, "service": "core_v0"})

    @app.get("/v1/version")
    def version():
        return jsonify({"ok": True, "product": "loomsci_core", "version": __version__, "api": "core/1"})

    @app.get("/v1/status")
    def status():
        return jsonify({"ok": True, **store.stats(db_conn())})

    @app.post("/v1/items")
    def items_create():
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return jsonify({"ok": False, "error": "json_required"}), 400
        requested_app = str(body.get("app") or getattr(g, "app_slug", "") or "")
        if getattr(g, "app_slug", None) and requested_app != g.app_slug:
            return jsonify({"ok": False, "error": "forbidden"}), 403
        try:
            item = store.create_item(
                db_conn(),
                app=requested_app,
                type=str(body.get("type") or ""),
                title=str(body.get("title") or ""),
                body=str(body.get("body") or ""),
                metadata=body.get("metadata") if isinstance(body.get("metadata"), dict) else {},
                tags=[str(tag) for tag in body.get("tags") or []],
                item_id=body.get("id"),
            )
        except ValueError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400
        return jsonify({"ok": True, "item": item}), 201

    @app.get("/v1/items")
    def items_list():
        app_name = getattr(g, "app_slug", None) or request.args.get("app", "")
        return jsonify({"ok": True, "items": store.list_items(
            db_conn(),
            app=app_name,
            type=request.args.get("type", ""),
            tag=request.args.get("tag", ""),
            limit=int(request.args.get("limit", "100")),
            offset=int(request.args.get("offset", "0")),
        )})

    @app.get("/v1/items/<item_id>")
    def items_get(item_id: str):
        item = store.get_item(db_conn(), item_id)
        if item is None or not allowed(item["app"]):
            return jsonify({"ok": False, "error": "not_found"}), 404
        return jsonify({"ok": True, "item": item})

    @app.patch("/v1/items/<item_id>")
    def items_patch(item_id: str):
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return jsonify({"ok": False, "error": "json_required"}), 400
        current = store.get_item(db_conn(), item_id)
        if current is None or not allowed(current["app"]):
            return jsonify({"ok": False, "error": "not_found"}), 404
        item = store.update_item(db_conn(), item_id, **body)
        if item is None:
            return jsonify({"ok": False, "error": "not_found"}), 404
        return jsonify({"ok": True, "item": item})

    @app.delete("/v1/items/<item_id>")
    def items_delete(item_id: str):
        current = store.get_item(db_conn(), item_id)
        if current is None or not allowed(current["app"]):
            return jsonify({"ok": False, "error": "not_found"}), 404
        if not store.delete_item(db_conn(), item_id):
            return jsonify({"ok": False, "error": "not_found"}), 404
        return jsonify({"ok": True, "deleted": item_id})

    @app.post("/v1/items/<item_id>/tags")
    def tags_set(item_id: str):
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or not isinstance(body.get("tags"), list):
            return jsonify({"ok": False, "error": "tags_required"}), 400
        current = store.get_item(db_conn(), item_id)
        if current is None or not allowed(current["app"]):
            return jsonify({"ok": False, "error": "not_found"}), 404
        return jsonify({"ok": True, "tags": store.set_tags(
            db_conn(), item_id=item_id,
            tags=[str(tag) for tag in body["tags"]],
            source=str(body.get("source") or "ai"),
        )})

    @app.get("/v1/tags")
    def tags_list():
        tags = store.list_tags(db_conn(), limit=int(request.args.get("limit", "100")))
        if getattr(g, "app_slug", None):
            tags = [tag for tag in tags if any(
                item["app"] == g.app_slug for item in store.list_items(db_conn(), tag=tag["tag"], limit=200)
            )]
        return jsonify({"ok": True, "tags": tags})

    @app.get("/v1/search")
    def search():
        return jsonify({"ok": True, "items": store.search(
            db_conn(), request.args.get("q", ""),
            limit=int(request.args.get("limit", "50")),
            app=getattr(g, "app_slug", None) or "",
        )})

    @app.post("/v1/blobs")
    def blobs_create():
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return jsonify({"ok": False, "error": "json_required"}), 400
        try:
            data = base64.b64decode(str(body.get("content_base64") or ""), validate=True)
            item_id = body.get("item_id")
            if getattr(g, "app_slug", None):
                item = store.get_item(db_conn(), str(item_id or ""))
                if item is None or not allowed(item["app"]):
                    return jsonify({"ok": False, "error": "forbidden"}), 403
            blob = store.add_blob(
                db_conn(),
                blob_dir=Path(app.config["BLOB_DIR"]),
                filename=str(body.get("filename") or "file"),
                content_type=str(body.get("content_type") or "application/octet-stream"),
                data=data,
                item_id=item_id,
            )
        except (ValueError, binascii.Error) as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400
        return jsonify({"ok": True, "blob": blob}), 201

    @app.get("/v1/blobs/<blob_id>")
    def blobs_get(blob_id: str):
        blob = store.get_blob(db_conn(), blob_id)
        if blob is None:
            return jsonify({"ok": False, "error": "not_found"}), 404
        if getattr(g, "app_slug", None):
            item = store.get_item(db_conn(), str(blob.get("item_id") or ""))
            if item is None or not allowed(item["app"]):
                return jsonify({"ok": False, "error": "not_found"}), 404
        path = Path(app.config["BLOB_DIR"]) / blob_id
        if not path.is_file():
            return jsonify({"ok": False, "error": "blob_missing"}), 404
        if request.args.get("inline") in {"1", "true", "yes"}:
            text = path.read_bytes()[:200_000].decode("utf-8", errors="replace")
            return jsonify({"ok": True, "blob": blob, "text": text, "truncated": path.stat().st_size > 200_000})
        response = Response(path.read_bytes(), mimetype=blob.get("content_type") or "application/octet-stream")
        response.headers["Content-Disposition"] = f'attachment; filename="{blob["filename"]}"'
        return response

    @app.post("/v1/apps/install")
    def apps_install():
        if getattr(g, "app_slug", None):
            return jsonify({"ok": False, "error": "forbidden"}), 403
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or not body.get("source"):
            return jsonify({"ok": False, "error": "source_required"}), 400
        try:
            result = app.config["HOST"].install(Path(str(body["source"])).expanduser())
        except (AppHostError, ValueError, OSError) as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400
        return jsonify({"ok": True, **result}), 201

    @app.post("/v1/apps/<slug>/start")
    def apps_start(slug: str):
        if getattr(g, "app_slug", None):
            return jsonify({"ok": False, "error": "forbidden"}), 403
        try:
            return jsonify({"ok": True, **app.config["HOST"].start(slug)})
        except AppHostError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.post("/v1/apps/<slug>/stop")
    def apps_stop(slug: str):
        if getattr(g, "app_slug", None):
            return jsonify({"ok": False, "error": "forbidden"}), 403
        return jsonify({"ok": True, **app.config["HOST"].stop(slug)})

    @app.post("/v1/apps/<slug>/update")
    def apps_update(slug: str):
        if getattr(g, "app_slug", None):
            return jsonify({"ok": False, "error": "forbidden"}), 403
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or not body.get("source"):
            return jsonify({"ok": False, "error": "source_required"}), 400
        try:
            return jsonify({"ok": True, **app.config["HOST"].update(slug, Path(str(body["source"])).expanduser())})
        except (AppHostError, ValueError, OSError) as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.delete("/v1/apps/<slug>")
    def apps_remove(slug: str):
        if getattr(g, "app_slug", None):
            return jsonify({"ok": False, "error": "forbidden"}), 403
        return jsonify({"ok": True, **app.config["HOST"].remove(slug)})

    @app.get("/v1/backups")
    def backups_list():
        if getattr(g, "app_slug", None):
            return jsonify({"ok": False, "error": "forbidden"}), 403
        return jsonify({"ok": True, "backups": backup_store.list_backups(Path(app.config["HOME"]))})

    @app.post("/v1/backups")
    def backups_create():
        if getattr(g, "app_slug", None):
            return jsonify({"ok": False, "error": "forbidden"}), 403
        try:
            path = backup_store.create(Path(app.config["HOME"]))
        except ValueError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400
        return jsonify({"ok": True, "backup": {"name": path.name, "path": str(path)}}), 201

    @app.post("/v1/backups/restore")
    def backups_restore():
        if getattr(g, "app_slug", None):
            return jsonify({"ok": False, "error": "forbidden"}), 403
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or not body.get("backup") or not body.get("target"):
            return jsonify({"ok": False, "error": "backup_and_target_required"}), 400
        try:
            result = backup_store.restore(Path(str(body["backup"])).expanduser(), Path(str(body["target"])).expanduser())
        except ValueError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400
        return jsonify({"ok": True, **result})

    @app.get("/v1/apps")
    def apps_list():
        rows = db_conn().execute("SELECT slug,version,manifest_json,installed_at FROM apps").fetchall()
        return jsonify({"ok": True, "apps": [dict(row) for row in rows]})

    return app


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--home", default=str(Path.home() / ".loomsci-core-v0"))
    parser.add_argument("--port", type=int, default=8795)
    args = parser.parse_args()
    create_app(
        Path(args.home), core_url=f"http://127.0.0.1:{args.port}"
    ).run(host="127.0.0.1", port=args.port, threaded=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
