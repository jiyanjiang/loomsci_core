#!/usr/bin/env python3
"""Minimal Core v0 HTTP server.

Exposes items, tags, blobs, search, apps, and backups behind a local token.
"""

from __future__ import annotations

import argparse
import atexit
import base64
import binascii
import secrets
import http.client
import subprocess
import urllib.parse
from pathlib import Path

from flask import Flask, Response, g, jsonify, redirect, request, send_file, send_from_directory

from . import backup as backup_store
from .version import __version__
from . import store
from . import catalog as catalog_store
from . import update as update_store
from .app_host import AppHost, AppHostError

WEB = Path(__file__).resolve().parent / "web"


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
    ui_session = secrets.token_hex(32)
    app = Flask(__name__)
    app.config["TOKEN"] = token
    app.config["UI_SESSION"] = ui_session
    app.config["HOME"] = str(home)
    app.config["DB"] = str(db)
    app.config["BLOB_DIR"] = str(home / "data" / "blobs")
    app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024
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

    spa_paths = {"/", "/app", "/version", "/tags", "/trash", "/tools", "/settings", "/site"}

    @app.before_request
    def auth():
        if request.path in {"/v1/health", "/v1/version"} or request.path in spa_paths or request.path.startswith("/item/"):
            return None
        if request.path.startswith("/assets/"):
            return None
        if request.path.startswith("/apps/") and request.method == "GET":
            return None
        if secrets.compare_digest(request.cookies.get("loomsci_ui", ""), ui_session):
            g.app_slug = None
            g.ui_session = True
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

    @app.get("/")
    @app.get("/app")
    def ui_index():
        html = (WEB / "index.html").read_text(encoding="utf-8")
        response = Response(html, mimetype="text/html")
        response.headers["Cache-Control"] = "no-store"
        response.set_cookie(
            "loomsci_ui", ui_session, httponly=True, samesite="Strict", path="/"
        )
        return response

    for _path in ("/version", "/tags", "/trash", "/tools", "/settings", "/site"):
        app.add_url_rule(_path, endpoint="ui_" + _path.strip("/"), view_func=ui_index)
    app.add_url_rule("/item/<item_id>", endpoint="ui_item", view_func=lambda item_id: ui_index())
    app.add_url_rule("/item/<item_id>/full", endpoint="ui_item_full", view_func=lambda item_id: ui_index())

    @app.route("/apps/<slug>", defaults={"subpath": ""}, methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
    @app.route("/apps/<slug>/", defaults={"subpath": ""}, methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
    @app.route("/apps/<slug>/<path:subpath>", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
    def app_proxy(slug: str, subpath: str):
        port = app.config["HOST"].port(slug)
        if not port:
            return jsonify({"ok": False, "error": "app_not_running"}), 404
        host = request.host.split(":", 1)[0].lower()
        if host in {"127.0.0.1", "localhost"}:
            core_port = request.host.rsplit(":", 1)[1] if ":" in request.host else "80"
            target = f"http://app-{slug}.localhost:{core_port}/apps/{slug}/"
            if subpath:
                target += subpath
            if request.query_string:
                target += "?" + request.query_string.decode("latin-1")
            return redirect(target, code=307)
        path = "/" + subpath
        if request.query_string:
            path += "?" + request.query_string.decode("latin-1")
        hop = {"connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
               "te", "trailers", "transfer-encoding", "upgrade", "host",
               "authorization", "x-loomsci-token"}
        headers = {}
        for key, value in request.headers.items():
            lower = key.lower()
            if lower in hop:
                continue
            if lower == "cookie":
                # App code runs on the Core origin. Never let it receive the
                # owner's UI session; preserve only app-owned cookies.
                kept = [
                    part for part in value.split(";")
                    if part.strip() and not part.strip().startswith("loomsci_ui=")
                ]
                if kept:
                    headers[key] = "; ".join(kept)
                continue
            headers[key] = value
        body = request.get_data()
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=60)
        try:
            connection.request(request.method, path, body=body or None, headers=headers)
            upstream = connection.getresponse()
            payload = upstream.read()
            response = Response(payload, status=upstream.status)
            for key, value in upstream.getheaders():
                if key.lower() in {"content-length", "connection", "transfer-encoding"}:
                    continue
                if key.lower() == "set-cookie" and value.lower().startswith("loomsci_ui="):
                    continue
                response.headers[key] = value
            response.headers["Content-Length"] = str(len(payload))
            # Apps live on a separate *.localhost origin; never mint the owner
            # UI session on that origin.
            return response
        except OSError as exc:
            return jsonify({"ok": False, "error": f"app_proxy: {exc}"}), 502
        finally:
            connection.close()

    @app.get("/assets/<path:filename>")
    def ui_static(filename: str):
        return send_from_directory(WEB, filename)

    @app.get("/v1/health")
    def health():
        return jsonify({"ok": True, "api": "core/1", "schema": store.SCHEMA_VERSION, "service": "core_v0"})

    @app.get("/v1/version")
    def version():
        return jsonify({"ok": True, "product": "loomsci_core", "version": __version__, "api": "core/1"})

    def update_home() -> Path:
        return Path(app.config["HOME"])

    @app.get("/v1/update/status")
    def update_status():
        if getattr(g, "app_slug", None):
            return jsonify({"ok": False, "error": "forbidden"}), 403
        return jsonify(update_store.status(update_home()))

    @app.post("/v1/update/check")
    def update_check():
        if getattr(g, "app_slug", None):
            return jsonify({"ok": False, "error": "forbidden"}), 403
        body = request.get_json(silent=True) or {}
        source = str(body.get("source") or "").strip() or None
        return jsonify(update_store.check(update_home(), source, force=bool(body.get("force"))))

    @app.post("/v1/update/download")
    def update_download():
        if getattr(g, "app_slug", None):
            return jsonify({"ok": False, "error": "forbidden"}), 403
        body = request.get_json(silent=True) or {}
        return jsonify(update_store.download(update_home(), force=bool(body.get("force"))))

    @app.post("/v1/update/apply")
    def update_apply():
        if getattr(g, "app_slug", None):
            return jsonify({"ok": False, "error": "forbidden"}), 403
        host = request.host or ""
        port = int(host.rsplit(":", 1)[1]) if ":" in host else 80
        return jsonify(update_store.apply_async(update_home(), port))

    @app.post("/v1/update/settings")
    def update_settings():
        if getattr(g, "app_slug", None):
            return jsonify({"ok": False, "error": "forbidden"}), 403
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return jsonify({"ok": False, "error": "json_required"}), 400
        return jsonify(update_store.settings(update_home(), **{
            key: body[key] for key in ("enabled", "mode", "channel", "manifest_url") if key in body
        }))

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
        current = store.get_item(db_conn(), item_id, include_deleted=True)
        if current is None or not allowed(current["app"]):
            return jsonify({"ok": False, "error": "not_found"}), 404
        hard = request.args.get("hard") in {"1", "true", "yes"}
        if not store.delete_item(db_conn(), item_id, hard=hard,
                                blob_dir=Path(app.config["BLOB_DIR"])):
            return jsonify({"ok": False, "error": "not_found"}), 404
        return jsonify({"ok": True, "deleted": item_id, "hard": hard})

    @app.get("/v1/trash")
    def trash_list():
        if getattr(g, "app_slug", None):
            return jsonify({"ok": False, "error": "forbidden"}), 403
        return jsonify({"ok": True, "items": store.list_deleted(
            db_conn(), limit=int(request.args.get("limit", "100")),
            offset=int(request.args.get("offset", "0")),
        )})

    @app.post("/v1/items/<item_id>/restore")
    def items_restore(item_id: str):
        current = store.get_item(db_conn(), item_id, include_deleted=True)
        if current is None or not allowed(current["app"]):
            return jsonify({"ok": False, "error": "not_found"}), 404
        if not store.restore_item(db_conn(), item_id):
            return jsonify({"ok": False, "error": "not_deleted"}), 400
        return jsonify({"ok": True, "item": store.get_item(db_conn(), item_id)})

    @app.post("/v1/trash/purge")
    def trash_purge():
        if getattr(g, "app_slug", None):
            return jsonify({"ok": False, "error": "forbidden"}), 403
        count = store.purge_deleted(db_conn(), blob_dir=Path(app.config["BLOB_DIR"]))
        return jsonify({"ok": True, "purged": count})

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
        tags = store.list_tags(
            db_conn(), limit=int(request.args.get("limit", "100")),
            app=getattr(g, "app_slug", None) or "",
        )
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
        return send_file(
            path, mimetype=blob.get("content_type") or "application/octet-stream",
            as_attachment=True, download_name=blob["filename"],
        )

    @app.get("/v1/catalog")
    def catalog_get():
        if getattr(g, "app_slug", None):
            return jsonify({"ok": False, "error": "forbidden"}), 403
        source = request.args.get("source", "")
        try:
            return jsonify({"ok": True, "catalog": catalog_store.load(source)})
        except (catalog_store.CatalogError, OSError) as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.post("/v1/apps/install")
    def apps_install():
        if getattr(g, "app_slug", None):
            return jsonify({"ok": False, "error": "forbidden"}), 403
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or not (body.get("source") or body.get("repo")):
            return jsonify({"ok": False, "error": "source_or_repo_required"}), 400
        try:
            if body.get("repo"):
                result = app.config["HOST"].install_repo(str(body["repo"]), str(body.get("ref") or ""))
            else:
                result = app.config["HOST"].install(Path(str(body["source"])).expanduser())
        except (AppHostError, ValueError, OSError, subprocess.SubprocessError) as exc:
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

    @app.post("/v1/backups/verify")
    def backups_verify():
        if getattr(g, "app_slug", None):
            return jsonify({"ok": False, "error": "forbidden"}), 403
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or not body.get("backup"):
            return jsonify({"ok": False, "error": "backup_required"}), 400
        try:
            manifest = backup_store.verify(Path(str(body["backup"])).expanduser())
        except (ValueError, OSError) as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400
        return jsonify({"ok": True, "manifest": manifest})

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
    app = create_app(
        Path(args.home), core_url=f"http://127.0.0.1:{args.port}"
    )
    update_store.start_scheduler(Path(args.home), args.port)
    app.run(host="127.0.0.1", port=args.port, threaded=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
