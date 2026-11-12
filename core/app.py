"""Minimal local HTTP app for the S1 Core slice."""

from __future__ import annotations

import base64
import binascii
import json
import time
from html import escape
from pathlib import Path
from urllib.parse import quote_plus
from typing import Mapping

from flask import Flask, Response, g, jsonify, redirect, request

from core import alice, handoff, llm_config, project_store, storage, summaries
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
    if isinstance(exc, (ValueError, binascii.Error)):
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
    app.config["MAX_CONTENT_LENGTH"] = 24 * 1024 * 1024
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
        if decision.agent and not storage.agent_exists(get_db(), decision.agent):
            return jsonify({"ok": False, "error": "unknown_agent"}), 403
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
<p><a href="/app/posts">Posts</a> · <a href="/app/tasks">Tasks</a> · <a href="/app/memory">Memory</a> · <a href="/app/inbox">Inbox</a></p>
<p><a href="/v1/meta/features">/v1/meta/features</a> · <a href="/v1/health">/v1/health</a></p>
</body>
</html>"""
        return Response(page, mimetype="text/html")

    def _data_shell(title: str, body: str) -> Response:
        page = f"""<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)} · loomsci_core</title>
<style>
:root {{ color-scheme: light dark; font-family: ui-sans-serif, system-ui, sans-serif; }}
body {{ max-width: 860px; margin: 6vh auto; padding: 0 24px; line-height: 1.5; }}
.item {{ border-top: 1px solid color-mix(in srgb, currentColor 18%, transparent); padding: 12px 0; }}
.meta {{ opacity: .65; font-size: 13px; }}
pre {{ white-space: pre-wrap; margin: 6px 0 0; }}
.compose {{ display: grid; gap: 8px; margin: 14px 0 22px; }}
.compose input, .compose textarea {{ width: 100%; box-sizing: border-box; padding: 8px; font: inherit; }}
.compose textarea {{ min-height: 72px; }}
.compose button {{ justify-self: start; padding: 6px 12px; font: inherit; }}
.fact {{ border-top: 1px solid color-mix(in srgb, currentColor 18%, transparent); padding: 12px 0; }}
.error {{ color: #b00020; }}
.fact form, .item form {{ display: inline; }}
.item form input {{ width: 12em; padding: 3px 6px; font: inherit; }}
.item form button {{ padding: 3px 8px; font: inherit; }}
.fact button {{ margin-right: 6px; padding: 3px 8px; font: inherit; }}
</style></head>
<body><p><a href="/app">← status</a></p><h1>{escape(title)}</h1>{body}</body></html>"""
        return Response(page, mimetype="text/html")

    def _ui_agent():
        record = alice.read_agent(layout.root)
        return str((record or {}).get("handle") or "")

    @app.get("/app/posts")
    def posts_page():
        posts = storage.list_posts(get_db(), limit=50)
        items = []
        for post in posts:
            body = escape(str(post.get("body") or ""))[:400]
            files = "".join(
                f'<div class="meta"><a href="/app/attachments/{escape(str(item["id"]))}">'
                f'{escape(str(item.get("filename") or item["id"]))}</a></div>'
                for item in post.get("attachments") or []
            )
            items.append(
                '<div class="item">'
                f'<div class="meta">#{post.get("seq")} · {escape(str(post.get("author") or ""))}'
                f' · {escape(str(post.get("kind") or ""))}</div>'
                f'<pre>{body}</pre>{files}</div>'
            )
        author = _ui_agent()
        form = (
            '<form class="compose" method="post" action="/app/posts">'
            '<textarea name="body" placeholder="Markdown body" required></textarea>'
            '<button type="submit">Post</button></form>'
            if author else '<p class="meta">Initialize an agent first: loomsci init</p>'
        )
        body = form + ("".join(items) or '<p class="meta">No posts yet.</p>')
        return _data_shell("Posts", body)

    @app.get("/app/tasks")
    def tasks_page():
        tasks = storage.list_tasks(get_db(), limit=50)
        items = []
        author = _ui_agent()
        for task in tasks:
            actions = ""
            status = str(task.get("status") or "")
            assigned = task.get("assigned_to")
            if author and status in {"backlog", "claimed"}:
                if not assigned or assigned == author:
                    actions += (
                        f'<form method="post" action="/app/tasks/{escape(str(task["id"]))}/claim">'
                        '<button type="submit">Claim</button></form>'
                    )
                if assigned == author:
                    actions += (
                        f'<form method="post" action="/app/tasks/{escape(str(task["id"]))}/done">'
                        '<input name="evidence" placeholder="Evidence" required>'
                        '<button type="submit">Done</button></form>'
                    )
                elif assigned:
                    actions += '<div class="meta">claimed by another agent; use the CLI</div>'
            items.append(
                '<div class="item">'
                f'<div><b>{escape(str(task.get("title") or task.get("id") or ""))}</b></div>'
                f'<div class="meta">{escape(status)}'
                f' · {escape(str(assigned or "unassigned"))}</div>'
                f'<pre>{escape(str(task.get("acceptance") or ""))[:400]}</pre>{actions}</div>'
            )
        form = (
            '<form class="compose" method="post" action="/app/tasks">'
            '<input name="title" placeholder="Task title" required maxlength="200">'
            '<textarea name="acceptance" placeholder="Acceptance criteria"></textarea>'
            '<button type="submit">Add task</button></form>'
            if author else '<p class="meta">Initialize an agent first: loomsci init</p>'
        )
        error = str(request.args.get("error") or "")
        error_html = f'<p class="error">{escape(error)}</p>' if error else ""
        body = error_html + form + ("".join(items) or '<p class="meta">No tasks yet.</p>')
        return _data_shell("Tasks", body)

    @app.post("/app/posts")
    def posts_create_page():
        author = _ui_agent()
        if not author:
            return redirect("/app")
        try:
            post = storage.create_post(
                get_db(),
                author=author,
                kind="note",
                body=str(request.form.get("body") or ""),
            )
            summaries.enqueue_for_post(
                get_db(), post_id=post["id"], body=post["body"], home=layout.root
            )
        except ValueError:
            pass
        return redirect("/app/posts")

    @app.post("/app/tasks")
    def tasks_create_page():
        author = _ui_agent()
        if not author:
            return redirect("/app")
        try:
            storage.create_task(
                get_db(),
                title=str(request.form.get("title") or ""),
                acceptance=str(request.form.get("acceptance") or ""),
            )
        except ValueError:
            pass
        return redirect("/app/tasks")

    @app.post("/app/tasks/<task_id>/claim")
    def tasks_claim_page(task_id: str):
        author = _ui_agent()
        if not author:
            return redirect("/app")
        try:
            storage.claim_task(get_db(), task_id=task_id, agent=author)
        except Exception as exc:  # noqa: BLE001 - show the failure
            return redirect("/app/tasks?error=" + quote_plus(str(exc)))
        return redirect("/app/tasks")

    @app.post("/app/tasks/<task_id>/done")
    def tasks_done_page(task_id: str):
        author = _ui_agent()
        if not author:
            return redirect("/app")
        evidence = str(request.form.get("evidence") or "").strip()
        if not evidence:
            return redirect("/app/tasks?error=" + quote_plus("evidence required"))
        try:
            storage.done_task(
                get_db(), task_id=task_id, agent=author, evidence=evidence
            )
        except Exception as exc:  # noqa: BLE001 - show the failure
            return redirect("/app/tasks?error=" + quote_plus(str(exc)))
        return redirect("/app/tasks")

    @app.get("/app/memory")
    def memory_page():
        author = _ui_agent()
        facts = storage.list_facts(get_db(), limit=100)
        items = []
        for fact in facts:
            buttons = "".join(
                f'<form method="post" action="/app/memory/{escape(str(fact["id"]))}/review">'
                f'<input type="hidden" name="status" value="{status}">'
                f'<button type="submit">{label}</button></form>'
                for status, label in (
                    ("approved", "Approve"), ("rejected", "Reject"), ("archived", "Archive")
                )
            )
            items.append(
                '<div class="fact">'
                f'<div><b>[{escape(str(fact.get("status") or ""))}]</b> '
                f'{escape(str(fact.get("claim") or ""))}</div>'
                f'<div class="meta">{escape(str(fact.get("id") or ""))}'
                f' · {escape(str(fact.get("source") or "no source"))}</div>'
                f'<pre>{escape(str(fact.get("evidence") or ""))[:400]}</pre>'
                f'{buttons}</div>'
            )
        form = (
            '<form class="compose" method="post" action="/app/memory">'
            '<input name="claim" placeholder="Fact / claim" required maxlength="500">'
            '<input name="source" placeholder="Source">'
            '<textarea name="evidence" placeholder="Evidence"></textarea>'
            '<button type="submit">Add candidate fact</button></form>'
            if author else '<p class="meta">Initialize an agent first: loomsci init</p>'
        )
        body = form + ("".join(items) or '<p class="meta">No facts yet.</p>')
        return _data_shell("Memory", body)

    @app.post("/app/memory")
    def memory_add_page():
        author = _ui_agent()
        if not author:
            return redirect("/app")
        try:
            storage.add_fact(
                get_db(),
                claim=str(request.form.get("claim") or ""),
                evidence=str(request.form.get("evidence") or ""),
                source=str(request.form.get("source") or ""),
                created_by=author,
            )
        except ValueError:
            pass
        return redirect("/app/memory")

    @app.post("/app/memory/<fact_id>/review")
    def memory_review_page(fact_id: str):
        author = _ui_agent()
        if not author:
            return redirect("/app")
        status = str(request.form.get("status") or "")
        try:
            storage.review_fact(
                get_db(), fact_id=fact_id, status=status, reviewer=author
            )
        except Exception:  # noqa: BLE001 - UI redirects on bad input
            pass
        return redirect("/app/memory")

    @app.get("/app/inbox")
    def inbox_page():
        author = _ui_agent()
        if not author:
            return _data_shell("Inbox", '<p class="meta">Initialize an agent first: loomsci init</p>')
        items = []
        for post in storage.list_inbox(get_db(), agent=author, limit=100):
            read = post.get("mention_read_at")
            items.append(
                '<div class="item">'
                f'<div class="meta">#{post.get("seq")} · {escape(str(post.get("author") or ""))}'
                f' · {"read" if read else "unread"}</div>'
                f'<pre>{escape(str(post.get("body") or ""))[:400]}</pre></div>'
            )
        body = "".join(items) or '<p class="meta">No mentions yet.</p>'
        return _data_shell("Inbox", body)

    @app.get("/app/attachments/<attachment_id>")
    def attachment_page(attachment_id: str):
        item = storage.get_attachment(get_db(), attachment_id)
        if item is None:
            return jsonify({"ok": False, "error": "not_found"}), 404
        target = layout.blobs / attachment_id
        if not target.is_file():
            return jsonify({"ok": False, "error": "blob_missing"}), 404
        response = Response(target.read_bytes(), mimetype=item.get("content_type") or "application/octet-stream")
        response.headers["Content-Disposition"] = f'attachment; filename="{item.get("filename") or "file"}"'
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
        if request.args.get("view") == "feed":
            for post in posts:
                if post["body_chars"] > summaries.SHORT_POST_MAX:
                    if not post.get("summary"):
                        post["summary"] = {
                            "text": summaries.fallback(post["body"]),
                            "status": "fallback",
                            "model": "extractive",
                            "error": None,
                        }
                    post["body"] = None
                    post["has_more"] = True
                else:
                    post["has_more"] = False
        return jsonify({"ok": True, "posts": posts})

    @app.get("/v1/posts/<post_id>")
    def posts_detail(post_id: str):
        post = storage.get_post(get_db(), post_id)
        if post is None:
            return jsonify({"ok": False, "error": "not_found"}), 404
        post["has_more"] = False
        return jsonify({"ok": True, "post": post})

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
                body=str(body.get("body") or ""),
                thread_id=body.get("thread_id"),
                parent_id=body.get("parent_id"),
                meta=body.get("meta") if isinstance(body.get("meta"), dict) else {},
                attachments=[str(item) for item in body.get("attachments") or []],
            )
            summaries.enqueue_for_post(
                get_db(), post_id=post["id"], body=post["body"], home=layout.root
            )
            post = storage.get_post(get_db(), post["id"]) or post
        except Exception as exc:  # noqa: BLE001 - mapped below
            return _storage_error(exc)
        return jsonify({"ok": True, "post": post}), 201

    @app.get("/v1/projects")
    def projects_list():
        selected = request.args.get("selected") in {"1", "true", "yes"}
        return jsonify({"ok": True, "projects": project_store.list_projects(get_db(), selected_only=selected)})

    @app.get("/v1/projects/<code>/stats")
    def projects_stats(code: str):
        try:
            return jsonify({"ok": True, **project_store.stats(get_db(), code)})
        except LookupError:
            return jsonify({"ok": False, "error": "not_found"}), 404

    @app.get("/v1/projects/<code>/entries")
    def projects_entries(code: str):
        try:
            limit = int(request.args.get("limit", "50"))
            offset = int(request.args.get("offset", "0"))
        except ValueError:
            return jsonify({"ok": False, "error": "bad_pagination"}), 400
        try:
            return jsonify({"ok": True, **project_store.entries(
                get_db(), code, kind=request.args.get("kind"), limit=limit, offset=offset
            )})
        except LookupError:
            return jsonify({"ok": False, "error": "not_found"}), 404

    @app.get("/v1/projects/<code>")
    def projects_show(code: str):
        project = project_store.get_project(get_db(), code)
        if project is None:
            return jsonify({"ok": False, "error": "not_found"}), 404
        return jsonify({"ok": True, "project": project})

    def _provider(provider: str):
        if provider not in llm_config.PROVIDERS:
            return None
        return provider

    @app.get("/v1/settings/llm/<provider>")
    def settings_provider_get(provider: str):
        if _provider(provider) is None:
            return jsonify({"ok": False, "error": "unknown_provider"}), 404
        return jsonify({"ok": True, "provider": llm_config.public(layout.root, provider)})

    @app.put("/v1/settings/llm/<provider>/key")
    def settings_provider_key(provider: str):
        if _provider(provider) is None:
            return jsonify({"ok": False, "error": "unknown_provider"}), 404
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or not isinstance(body.get("api_key"), str):
            return jsonify({"ok": False, "error": "api_key_required"}), 400
        return jsonify({"ok": True, "provider": llm_config.set_key(layout.root, provider, body["api_key"])})

    @app.put("/v1/settings/llm/<provider>")
    def settings_provider_put(provider: str):
        if _provider(provider) is None:
            return jsonify({"ok": False, "error": "unknown_provider"}), 404
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return jsonify({"ok": False, "error": "json_object_required"}), 400
        return jsonify({"ok": True, "provider": llm_config.set_fields(
            layout.root, provider,
            base_url=body.get("base_url") if isinstance(body.get("base_url"), str) else None,
            model=body.get("model") if isinstance(body.get("model"), str) else None,
        )})

    @app.post("/v1/settings/llm/<provider>/test")
    def settings_provider_test(provider: str):
        if _provider(provider) is None:
            return jsonify({"ok": False, "error": "unknown_provider"}), 404
        return jsonify(llm_config.test_connection(layout.root, provider))

    @app.get("/v1/search")
    def search_all():
        q = str(request.args.get("q") or "").strip()
        try:
            limit = int(request.args.get("limit", "50"))
        except ValueError:
            return jsonify({"ok": False, "error": "invalid_limit"}), 400
        return jsonify({"ok": True, "results": storage.search(get_db(), q=q, limit=limit)})

    @app.get("/v1/inbox")
    def inbox_list():
        try:
            limit = int(request.args.get("limit", "50"))
        except ValueError:
            return jsonify({"ok": False, "error": "invalid_limit"}), 400
        items = storage.list_inbox(
            get_db(),
            agent=g.loomsci_agent,
            unread_only=request.args.get("unread") in ("1", "true", "yes"),
            limit=limit,
        )
        return jsonify({"ok": True, "inbox": items})

    @app.post("/v1/inbox/read")
    def inbox_read():
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return jsonify({"ok": False, "error": "json_object_required"}), 400
        try:
            changed = storage.mark_inbox_read(
                get_db(),
                agent=g.loomsci_agent,
                post_id=body.get("post_id"),
                up_to_seq=body.get("up_to_seq"),
            )
        except Exception as exc:  # noqa: BLE001 - mapped below
            return _storage_error(exc)
        return jsonify({"ok": True, "changed": changed})

    @app.post("/v1/attachments")
    def attachments_upload():
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return jsonify({"ok": False, "error": "json_object_required"}), 400
        try:
            data = base64.b64decode(str(body.get("content_base64") or ""), validate=True)
            meta = body.get("meta") if isinstance(body.get("meta"), dict) else {}
            for key in ("origin", "asset_kind", "rights", "source_url", "generator"):
                if body.get(key):
                    meta[key] = body.get(key)
            attachment = storage.add_attachment(
                get_db(),
                filename=str(body.get("filename") or "file"),
                content_type=str(body.get("content_type") or "application/octet-stream"),
                data=data,
                blob_dir=layout.blobs,
                meta=meta,
            )
        except Exception as exc:  # noqa: BLE001 - mapped below
            return _storage_error(exc)
        return jsonify({"ok": True, "attachment": attachment}), 201

    @app.get("/v1/attachments/<attachment_id>")
    def attachments_get(attachment_id: str):
        item = storage.get_attachment(get_db(), attachment_id)
        if item is None:
            return jsonify({"ok": False, "error": "not_found"}), 404
        target = layout.blobs / attachment_id
        if not target.is_file():
            return jsonify({"ok": False, "error": "blob_missing"}), 404
        response = Response(target.read_bytes(), mimetype=item.get("content_type") or "application/octet-stream")
        response.headers["Content-Disposition"] = f'attachment; filename="{item.get("filename") or "file"}"'
        return response

    @app.get("/v1/status")
    def status():
        return jsonify({"ok": True, "home": str(layout.root), **storage.stats(get_db())})

    @app.get("/v1/events")
    def events():
        try:
            since = int(request.args.get("since", "0"))
        except ValueError:
            return jsonify({"ok": False, "error": "bad_since"}), 400
        once = request.args.get("once") in ("1", "true", "yes")

        def generate():
            conn = storage.connect(layout.db)
            cursor = max(0, since)
            last_ping = time.monotonic()
            try:
                yield "retry: 1000\n\n"
                while True:
                    posts = storage.list_posts(conn, since=cursor, limit=100)
                    if posts:
                        for post in posts:
                            cursor = max(cursor, int(post["seq"]))
                            yield "event: post\ndata: " + json.dumps(post, ensure_ascii=False) + "\n\n"
                        last_ping = time.monotonic()
                        continue
                    if once:
                        return
                    if time.monotonic() - last_ping >= 15:
                        yield ": ping\n\n"
                        last_ping = time.monotonic()
                    time.sleep(1)
            finally:
                conn.close()

        response = Response(generate(), mimetype="text/event-stream")
        response.headers["Cache-Control"] = "no-cache"
        response.headers["X-Accel-Buffering"] = "no"
        return response

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

    @app.get("/v1/memory")
    def memory_list():
        try:
            limit = int(request.args.get("limit", "50"))
        except ValueError:
            return jsonify({"ok": False, "error": "invalid_limit"}), 400
        facts = storage.list_facts(
            get_db(),
            q=str(request.args.get("q") or ""),
            status=request.args.get("status") or None,
            project=request.args.get("project") or None,
            limit=limit,
        )
        return jsonify({"ok": True, "facts": facts})

    @app.post("/v1/memory")
    def memory_add():
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return jsonify({"ok": False, "error": "json_object_required"}), 400
        try:
            fact = storage.add_fact(
                get_db(),
                claim=str(body.get("claim") or ""),
                evidence=str(body.get("evidence") or ""),
                source=str(body.get("source") or ""),
                project=str(body.get("project") or ""),
                tags=str(body.get("tags") or ""),
                created_by=g.loomsci_agent,
                confidence=body.get("confidence"),
            )
        except Exception as exc:  # noqa: BLE001 - mapped below
            return _storage_error(exc)
        return jsonify({"ok": True, "fact": fact}), 201

    @app.post("/v1/memory/<fact_id>/review")
    def memory_review(fact_id: str):
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return jsonify({"ok": False, "error": "json_object_required"}), 400
        try:
            fact = storage.review_fact(
                get_db(),
                fact_id=fact_id,
                status=str(body.get("status") or ""),
                reviewer=g.loomsci_agent,
            )
        except Exception as exc:  # noqa: BLE001 - mapped below
            return _storage_error(exc)
        return jsonify({"ok": True, "fact": fact})

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
            summaries.enqueue_for_post(
                get_db(), post_id=post["id"], body=post["body"], home=layout.root
            )
            post = storage.get_post(get_db(), post["id"]) or post
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
