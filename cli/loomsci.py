"""loomsci command-line interface."""

from __future__ import annotations

import argparse
import base64
import getpass
import json
import os
import socket
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from core import addon_runtime
from core import backup as backup_mod
from core import storage_ops
from core import addons as addons_mod
from core import export as export_mod
from core import storage
from core.home import (
    HomeError,
    apply_migration,
    default_home,
    ensure_layout,
    migration_plan,
    resolve_home,
)
from core.local_auth import is_loopback_host, normalize_agent
from core.packs import Registry

DEFAULT_URL = "http://127.0.0.1:8787"


class CliError(RuntimeError):
    pass


def _json_print(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def _request(args: argparse.Namespace, method: str, path: str, body: dict | None = None) -> dict:
    data = None
    headers: dict[str, str] = {}
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if getattr(args, "agent", None):
        headers["X-Loomsci-Agent"] = str(args.agent)
    request = urllib.request.Request(
        args.url.rstrip("/") + path, data=data, headers=headers, method=method
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            raw = response.read().decode("utf-8", "replace")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        try:
            payload = json.loads(raw)
        except ValueError:
            payload = {"error": raw[:200]}
        raise CliError(
            f"HTTP {exc.code}: {payload.get('error') or 'request failed'}"
        ) from None
    except urllib.error.URLError as exc:
        raise CliError(f"cannot reach {args.url}: {exc.reason}") from None


def _require_agent(args: argparse.Namespace) -> str:
    if not getattr(args, "agent", None):
        raise CliError("--as <agent.owner> is required for this command")
    return str(args.agent)


def _cmd_home(args: argparse.Namespace) -> int:
    resolution = resolve_home(explicit=args.home)
    payload = {
        "path": str(resolution.path),
        "source": resolution.source,
        "legacy": resolution.legacy,
        "needs_migration": resolution.needs_migration,
    }
    if args.json:
        _json_print(payload)
    else:
        print(f"home: {payload['path']}")
        print(f"source: {payload['source']}")
        if resolution.needs_migration:
            print("legacy home detected; run: loomsci migrate --from <legacy> --apply")
    return 0


def _cmd_migrate(args: argparse.Namespace) -> int:
    source = Path(args.source).expanduser()
    destination = Path(args.to).expanduser() if args.to else default_home()
    plan = migration_plan(source, destination)
    result = apply_migration(plan, dry_run=not args.apply)
    if args.json:
        _json_print(result)
    else:
        mode = "dry-run" if result["dry_run"] else "applied"
        print(f"migrate ({mode}): {result['source']} -> {result['destination']}")
        print("items: " + (", ".join(result["items"]) or "(none)"))
        print("counts: " + json.dumps(result["counts"], ensure_ascii=False, sort_keys=True))
        for warning in result["warnings"]:
            print(f"warning: {warning}")
        if result["dry_run"]:
            print("no files were written; re-run with --apply to migrate")
    return 0


def _port_available(host: str, port: int) -> bool:
    if port == 0:
        return True
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    sock = socket.socket(family, socket.SOCK_STREAM)
    try:
        if os.name == "nt" and hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        else:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((host, port))
        return True
    except OSError:
        return False
    finally:
        sock.close()


def _cmd_serve(args: argparse.Namespace) -> int:
    if not is_loopback_host(args.host):
        print("error: the Core profile only binds a loopback host", file=sys.stderr)
        return 2
    if not _port_available(args.host, args.port):
        print(f"error: port {args.port} is already in use on {args.host}", file=sys.stderr)
        return 2
    from core.app import create_app

    app = create_app(home=args.home)
    app.run(
        host=args.host,
        port=args.port,
        threaded=True,
        use_reloader=False,
        debug=False,
    )
    return 0


def _cmd_features(args: argparse.Namespace) -> int:
    features = Registry.from_env().features()
    if args.json:
        _json_print(features)
    else:
        print(f"profile: {features['profile']}")
        print(f"packs: {', '.join(features['packs'])}")
        print(f"routes: {features['route_count']}")
        print(f"jobs: {', '.join(features['jobs']) or '(none)'}")
        print(f"nav: {', '.join(features['nav'])}")
    return 0


def _cmd_post(args: argparse.Namespace) -> int:
    _require_agent(args)
    attachment_ids = []
    for raw_path in args.attach or []:
        path = Path(raw_path).expanduser()
        data = path.read_bytes()
        uploaded = _request(
            args,
            "POST",
            "/v1/attachments",
            {
                "filename": path.name,
                "content_type": "application/octet-stream",
                "content_base64": base64.b64encode(data).decode("ascii"),
            },
        )
        attachment_ids.append(uploaded["attachment"]["id"])
    payload = {
        "kind": args.kind,
        "title": args.title or "",
        "body": args.body,
        "thread_id": args.thread,
        "parent_id": args.parent,
        "meta": {"to": args.to} if args.to else {},
        "attachments": attachment_ids,
    }
    result = _request(args, "POST", "/v1/posts", payload)
    if args.json:
        _json_print(result)
    else:
        print(f"posted: {result.get('post', {}).get('id', '?')}")
    return 0


def _cmd_read(args: argparse.Namespace) -> int:
    _require_agent(args)
    if args.since is None:
        cursor = int(_request(args, "GET", "/v1/read?scope=posts").get("cursor", 0))
    else:
        cursor = int(args.since)
    query = f"/v1/posts?since={cursor}&limit={args.limit}"
    if args.thread:
        query += f"&thread={urllib.parse.quote(args.thread)}"
    result = _request(args, "GET", query)
    posts = result.get("posts") or []
    if posts and not args.no_update:
        last_seq = max(int(post.get("seq", 0)) for post in posts)
        _request(
            args,
            "POST",
            "/v1/read",
            {"scope": "posts", "last_seq": last_seq},
        )
    if args.json:
        _json_print(result)
    else:
        for post in posts:
            body = " ".join(str(post.get("body") or "").split())
            title = str(post.get("title") or "").strip()
            print(
                f"{post.get('seq')} {post.get('id')} {post.get('author')} "
                f"{post.get('kind')} {title} :: {body[:160]}".rstrip()
            )
        if not posts:
            print("(no new posts)")
    return 0


def _cmd_presence(args: argparse.Namespace) -> int:
    _require_agent(args)
    if args.list or not args.tool:
        result = _request(args, "GET", "/v1/presence")
        if args.json:
            _json_print(result)
        else:
            for item in result.get("presence") or []:
                print(
                    f"{item.get('agent')} {item.get('tool')} "
                    f"{item.get('workspace')} {item.get('last_seen')}"
                )
        return 0
    payload = {
        "tool": args.tool,
        "workspace": args.workspace or "",
        "model": args.model or "",
        "pid": args.pid,
    }
    result = _request(args, "POST", "/v1/presence", payload)
    if args.json:
        _json_print(result)
    else:
        print(f"presence: {result.get('agent')} {result.get('tool')}")
    return 0


def _cmd_handoff(args: argparse.Namespace) -> int:
    _require_agent(args)
    payload = {
        "task_id": args.task,
        "to": args.to,
        "completed": args.completed or [],
        "remaining": args.remaining or [],
        "next": args.next or [],
        "risks": args.risks or [],
        "evidence": args.evidence,
    }
    result = _request(args, "POST", "/v1/handoff", payload)
    if args.json:
        _json_print(result)
    else:
        print(f"handoff posted: {result.get('post', {}).get('id', '?')}")
    return 0


def _alice_module():
    from core import alice as alice_mod
    return alice_mod


def _layout(args: argparse.Namespace):
    resolution = resolve_home(explicit=args.home)
    if resolution.needs_migration:
        raise CliError("legacy home detected; run `loomsci migrate` first")
    return ensure_layout(resolution.path)


def _cmd_alice_init(args: argparse.Namespace) -> int:
    layout = _layout(args)
    alice_mod = _alice_module()
    record = alice_mod.ensure(layout.root, args.owner, args.short)
    storage.init_db(layout.db)
    conn = storage.connect(layout.db)
    try:
        storage.ensure_agent(conn, record["handle"])
        conn.commit()
    finally:
        conn.close()
    if args.json:
        _json_print(record)
    else:
        print(f"alice: {record['handle']}")
    return 0


def _cmd_alice_show(args: argparse.Namespace) -> int:
    layout = _layout(args)
    alice_mod = _alice_module()
    record = alice_mod.read_agent(layout.root, args.short)
    if not record:
        raise CliError(f"agent not initialized: {args.short}")
    if args.json:
        _json_print(record)
    else:
        print(f"agent: {record.get('handle')}")
        print(f"role: {record.get('role')}")
    return 0


def _cmd_alice_review(args: argparse.Namespace) -> int:
    layout = _layout(args)
    alice_mod = _alice_module()
    result = alice_mod.review(layout.root, args.short)
    if args.json:
        _json_print(result)
    else:
        agent = result.get("agent") or {}
        print(f"agent: {agent.get('handle')}")
        print(f"versions: {len(result.get('versions') or [])}")
        for item in result.get("versions") or []:
            print(f"- {item['name']}")
    return 0


def _cmd_alice_snapshot(args: argparse.Namespace) -> int:
    layout = _layout(args)
    alice_mod = _alice_module()
    path = alice_mod.snapshot(layout.root, args.short, args.reason)
    if args.json:
        _json_print({"ok": True, "snapshot": str(path)})
    else:
        print(f"snapshot: {path}")
    return 0


def _cmd_alice_reset(args: argparse.Namespace) -> int:
    layout = _layout(args)
    alice_mod = _alice_module()
    result = alice_mod.reset(
        layout.root, args.short, keep_memory=not args.drop_memory
    )
    if args.json:
        _json_print(result)
    else:
        print("alice reset")
    return 0


def _cmd_alice_rename(args: argparse.Namespace) -> int:
    layout = _layout(args)
    alice_mod = _alice_module()
    storage.init_db(layout.db)
    conn = storage.connect(layout.db)
    try:
        record = alice_mod.rename(
            layout.root, conn, args.short, args.to, owner=args.owner
        )
    finally:
        conn.close()
    if args.json:
        _json_print(record)
    else:
        print(f"renamed: {record['handle']}")
    return 0


def _cmd_task_add(args: argparse.Namespace) -> int:
    _require_agent(args)
    result = _request(
        args,
        "POST",
        "/v1/tasks",
        {
            "title": args.title,
            "description": args.description or "",
            "acceptance": args.acceptance or "",
        },
    )
    if args.json:
        _json_print(result)
    else:
        print(f"task: {result.get('task', {}).get('id', '?')}")
    return 0


def _cmd_task_list(args: argparse.Namespace) -> int:
    _require_agent(args)
    query = f"/v1/tasks?limit={args.limit}"
    if args.status:
        query += f"&status={urllib.parse.quote(args.status)}"
    if args.mine:
        query += f"&assigned_to={urllib.parse.quote(str(args.agent))}"
    result = _request(args, "GET", query)
    if args.json:
        _json_print(result)
    else:
        for task in result.get("tasks") or []:
            print(
                f"{task.get('id')} {task.get('status')} "
                f"{task.get('assigned_to') or '-'} {task.get('title')}"
            )
    return 0


def _cmd_task_claim(args: argparse.Namespace) -> int:
    _require_agent(args)
    result = _request(
        args,
        "POST",
        f"/v1/tasks/{args.task_id}/claim",
        {"lease_seconds": args.lease},
    )
    if args.json:
        _json_print(result)
    else:
        print(f"claimed: {result.get('task', {}).get('id', '?')}")
    return 0


def _cmd_task_done(args: argparse.Namespace) -> int:
    _require_agent(args)
    result = _request(
        args,
        "POST",
        f"/v1/tasks/{args.task_id}/done",
        {"evidence": args.evidence},
    )
    if args.json:
        _json_print(result)
    else:
        print(f"done: {result.get('task', {}).get('id', '?')}")
    return 0


def _cmd_agent_add(args: argparse.Namespace) -> int:
    handle = normalize_agent(args.handle)
    if not handle:
        raise CliError("handle must be <agent>.<owner>")
    short, _, owner = handle.partition(".")
    layout = _layout(args)
    alice_mod = _alice_module()
    record = alice_mod.ensure(
        layout.root,
        owner,
        short,
        role=args.role or "collaborator",
        default_tool=args.tool,
    )
    storage.init_db(layout.db)
    conn = storage.connect(layout.db)
    try:
        storage.ensure_agent(conn, record["handle"])
        conn.commit()
    finally:
        conn.close()
    if args.json:
        _json_print(record)
    else:
        print(f"agent: {record['handle']} ({record.get('role')})")
    return 0


def _cmd_agent_list(args: argparse.Namespace) -> int:
    layout = _layout(args)
    alice_mod = _alice_module()
    by_handle: dict[str, dict] = {}
    agents_dir = layout.root / "agents"
    if agents_dir.is_dir():
        for path in sorted(agents_dir.iterdir()):
            if not path.is_dir():
                continue
            record = alice_mod.read_agent(layout.root, path.name)
            if record:
                record["source"] = "home"
                by_handle[str(record.get("handle"))] = record
    if getattr(args, "all", False):
        storage.init_db(layout.db)
        conn = storage.connect(layout.db)
        try:
            for row in storage.list_agents(conn):
                handle = str(row["handle"])
                by_handle.setdefault(handle, {"handle": handle, "source": "db"})
        finally:
            conn.close()
    entries = [by_handle[key] for key in sorted(by_handle)]
    if args.json:
        _json_print({"agents": entries})
    else:
        for record in entries:
            print(
                f"{record.get('handle')} role={record.get('role') or '-'} "
                f"tool={record.get('default_tool') or '-'} "
                f"source={record.get('source', 'home')}"
            )
    return 0


def _cmd_agent_prune(args: argparse.Namespace) -> int:
    layout = _layout(args)
    storage.init_db(layout.db)
    conn = storage.connect(layout.db)
    candidates = []
    try:
        for row in storage.list_agents(conn):
            short = str(row["handle"]).partition(".")[0]
            if not (layout.root / "agents" / short / "agent.json").is_file():
                candidates.append(str(row["handle"]))
        removed = []
        if args.yes:
            for handle in candidates:
                if storage.delete_agent(conn, handle):
                    removed.append(handle)
    finally:
        conn.close()
    payload = {"removed": removed, "would_remove": candidates, "dry_run": not args.yes}
    if args.json:
        _json_print(payload)
    elif not args.yes:
        print("would remove: " + (", ".join(candidates) or "(none)"))
        print("no changes; re-run with --yes to delete")
    else:
        print("removed: " + (", ".join(removed) or "(none)"))
    return 0


def _cmd_init(args: argparse.Namespace) -> int:
    owner = (args.owner or getpass.getuser()).strip().lower()
    layout = _layout(args)
    alice_mod = _alice_module()
    record = alice_mod.ensure(layout.root, owner, args.agent)
    storage.init_db(layout.db)
    conn = storage.connect(layout.db)
    try:
        storage.ensure_agent(conn, record["handle"])
        conn.commit()
    finally:
        conn.close()
    if args.json:
        _json_print(record)
    else:
        print(f"initialized: {layout.root}")
        print(f"agent: {record['handle']}")
    return 0


def _cmd_memory_add(args: argparse.Namespace) -> int:
    _require_agent(args)
    result = _request(
        args,
        "POST",
        "/v1/memory",
        {
            "claim": args.claim,
            "evidence": args.evidence or "",
            "source": args.source or "",
            "project": args.project or "",
            "tags": args.tags or "",
            "confidence": args.confidence,
        },
    )
    if args.json:
        _json_print(result)
    else:
        print(f"fact: {result.get('fact', {}).get('id', '?')}")
    return 0


def _cmd_memory_list(args: argparse.Namespace) -> int:
    _require_agent(args)
    query = f"/v1/memory?limit={args.limit}"
    for key, value in (("q", args.q), ("status", args.status), ("project", args.project)):
        if value:
            query += f"&{key}={urllib.parse.quote(str(value))}"
    result = _request(args, "GET", query)
    if args.json:
        _json_print(result)
    else:
        for fact in result.get("facts") or []:
            print(
                f"{fact.get('id')} [{fact.get('status')}] "
                f"{fact.get('claim')}"
            )
    return 0


def _cmd_memory_review(args: argparse.Namespace) -> int:
    _require_agent(args)
    result = _request(
        args,
        "POST",
        f"/v1/memory/{args.fact_id}/review",
        {"status": args.status},
    )
    if args.json:
        _json_print(result)
    else:
        print(f"fact: {result.get('fact', {}).get('id', '?')} -> {args.status}")
    return 0


def _cmd_search(args: argparse.Namespace) -> int:
    _require_agent(args)
    result = _request(
        args, "GET", f"/v1/search?q={urllib.parse.quote(args.query)}&limit={args.limit}"
    )
    if args.json:
        _json_print(result)
    else:
        for item in result.get("results") or []:
            print(f"[{item.get('type')}] {item.get('id')} {item.get('title')}")
    return 0


def _cmd_inbox(args: argparse.Namespace) -> int:
    _require_agent(args)
    if args.read or args.read_all:
        payload = {"post_id": args.read} if args.read else {"up_to_seq": 2**31 - 1}
        result = _request(args, "POST", "/v1/inbox/read", payload)
        if args.json:
            _json_print(result)
        else:
            print(f"marked read: {result.get('changed', 0)}")
        return 0
    query = f"/v1/inbox?limit={args.limit}"
    if args.unread:
        query += "&unread=1"
    result = _request(args, "GET", query)
    if args.json:
        _json_print(result)
    else:
        for post in result.get("inbox") or []:
            print(f"{post.get('id')} @{post.get('author')} {post.get('title') or ''}")
    return 0


def _cmd_watch(args: argparse.Namespace) -> int:
    _require_agent(args)
    query = f"/v1/events?since={args.since}"
    if args.once:
        query += "&once=1"
    headers = {"X-Loomsci-Agent": str(args.agent)}
    request = urllib.request.Request(args.url.rstrip("/") + query, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=args.timeout) as response:
            for raw in response:
                line = raw.decode("utf-8", "replace").rstrip("\n")
                if not line.startswith("data: "):
                    continue
                payload = json.loads(line[6:])
                if args.json:
                    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
                else:
                    print(f"#{payload.get('seq')} {payload.get('author')}: {payload.get('title') or payload.get('body', '')[:80]}")
    except urllib.error.HTTPError as exc:
        raise CliError(f"HTTP {exc.code}") from None
    except urllib.error.URLError as exc:
        raise CliError(f"cannot reach {args.url}: {exc.reason}") from None
    return 0


def _cmd_status(args: argparse.Namespace) -> int:
    _require_agent(args)
    result = _request(args, "GET", "/v1/status")
    if args.json:
        _json_print(result)
    else:
        print(f"home: {result.get('home')}")
        print(f"integrity: {result.get('integrity')}")
        print(f"last_seq: {result.get('last_seq')}")
        print("counts: " + json.dumps(result.get("counts") or {}, sort_keys=True))
    return 0


def _cmd_addon_list(args: argparse.Namespace) -> int:
    layout = _layout(args)
    records = {name: addons_mod.record(layout.root, name) for name in addons_mod.installed(layout.root)}
    entries = []
    for item in addons_mod.available():
        name = item["name"]
        rec = records.get(name, {})
        entries.append({
            **item,
            "installed": name in records,
            "installed_version": rec.get("version"),
            "installed_package": rec.get("package"),
            "update_available": bool(rec) and rec.get("version") != item.get("version"),
        })
    if args.json:
        _json_print({"addons": entries, "profiles": addons_mod.PROFILES})
    else:
        for item in entries:
            mark = "*" if item["installed"] else " "
            update = " UPDATE" if item["update_available"] else ""
            print(f"{mark} {item['name']:<12} {item.get('version', '?'):<8} {item.get('api', '')}{update}")
        print("profiles: " + ", ".join(addons_mod.PROFILES))
    return 0


def _cmd_addon_install(args: argparse.Namespace) -> int:
    layout = _layout(args)
    try:
        result = addons_mod.install(layout.root, args.name)
        if args.start:
            result["runtime"] = addon_runtime.start(layout.root, args.name)
    except (addons_mod.AddonError, addon_runtime.AddonRuntimeError) as exc:
        raise CliError(str(exc)) from None
    if args.json:
        _json_print(result)
    else:
        print(f"installed: {result['name']} {result['version'] or ''} -> {result['package']}".rstrip())
    return 0


def _cmd_addon_update(args: argparse.Namespace) -> int:
    layout = _layout(args)
    try:
        if args.all:
            result = addons_mod.update_all(layout.root)
        elif args.name:
            result = addons_mod.update(layout.root, args.name)
        else:
            raise CliError("specify an add-on name or --all")
    except addons_mod.AddonError as exc:
        raise CliError(str(exc)) from None
    if args.json:
        _json_print({"updated": result})
    else:
        items = result if isinstance(result, list) else [result]
        for item in items:
            print(f"updated: {item['name']} {item.get('previous_version') or '?'} -> {item.get('version') or '?'}")
    return 0


def _cmd_addon_verify(args: argparse.Namespace) -> int:
    layout = _layout(args)
    result = addons_mod.verify(layout.root)
    if args.json:
        _json_print(result)
    else:
        for item in result["addons"]:
            print(f"{'ok' if item['ok'] else 'FAIL'} {item['name']} {item.get('version') or '?'}")
    return 0 if result["ok"] else 1


def _cmd_addon_start(args: argparse.Namespace) -> int:
    layout = _layout(args)
    try:
        if args.all:
            result = addon_runtime.start_all(layout.root)
        elif args.name:
            result = addon_runtime.start(layout.root, args.name)
        else:
            raise CliError("specify an add-on name or --all")
    except addon_runtime.AddonRuntimeError as exc:
        raise CliError(str(exc)) from None
    if args.json:
        _json_print({"started": result})
    else:
        items = result if isinstance(result, list) else [result]
        for item in items:
            print(f"{item.get('name')}: {item.get('state', 'error')}" + (f" ({item.get('error')})" if item.get("error") else ""))
    return 0 if not isinstance(result, list) or all(item.get("running") for item in result) else 1


def _cmd_addon_stop(args: argparse.Namespace) -> int:
    layout = _layout(args)
    if args.all:
        result = addon_runtime.stop_all(layout.root)
    elif args.name:
        result = addon_runtime.stop(layout.root, args.name)
    else:
        raise CliError("specify an add-on name or --all")
    if args.json:
        _json_print({"stopped": result})
    else:
        items = result if isinstance(result, list) else [result]
        for item in items:
            print(f"{item['name']}: stopped={item.get('stopped')} running={item.get('running')}")
    return 0


def _cmd_addon_status(args: argparse.Namespace) -> int:
    layout = _layout(args)
    result = addon_runtime.status_all(layout.root)
    if args.json:
        _json_print({"addons": result})
    else:
        for item in result:
            print(f"{item['name']:<12} {item['state']:<12} pid={item.get('pid') or '-'} port={item.get('port') or '-'}")
    return 0


def _cmd_addon_remove(args: argparse.Namespace) -> int:
    layout = _layout(args)
    try:
        addon_runtime.stop(layout.root, args.name)
    except addon_runtime.AddonRuntimeError:
        pass
    result = addons_mod.remove(layout.root, args.name)
    if args.json:
        _json_print(result)
    else:
        print(f"removed: {result['name']}")
    return 0


def _cmd_addon_profile(args: argparse.Namespace) -> int:
    layout = _layout(args)
    try:
        result = addons_mod.install_profile(layout.root, args.profile)
        if args.start:
            for item in result:
                item["runtime"] = addon_runtime.start(layout.root, item["name"])
    except (addons_mod.AddonError, addon_runtime.AddonRuntimeError) as exc:
        raise CliError(str(exc)) from None
    if args.json:
        _json_print({"profile": args.profile, "installed": result})
    else:
        print(f"profile {args.profile}: " + (", ".join(item["name"] for item in result) or "(core)"))
    return 0


def _cmd_storage_report(args: argparse.Namespace) -> int:
    layout = _layout(args)
    result = storage_ops.report(layout.root)
    if args.json:
        _json_print(result)
    else:
        print(f"home: {result['home']}")
        print(f"db: {result['db_bytes']} bytes")
        print(f"blobs: {result['blob_bytes']} logical / {result['blob_disk_bytes']} disk bytes")
        print(f"attachments: {result['attachments']['count']} / {result['attachments']['bytes']} bytes")
        print(f"duplicates: {result['duplicates']['groups_count']} groups / {result['duplicates']['reclaimable_bytes']} reclaimable")
        print(f"orphans: {result['orphans']['count']} / {result['orphans']['bytes']} bytes")
        print(f"logs: {result['logs_bytes']} bytes; derived: {result['derived_cache_bytes']} bytes")
    return 0


def _cmd_storage_duplicates(args: argparse.Namespace) -> int:
    layout = _layout(args)
    result = storage_ops.duplicates(layout.root)
    if args.json:
        _json_print(result)
    else:
        print(f"groups: {result['groups_count']} reclaimable={result['reclaimable_bytes']} bytes")
        for group in result["groups"][:20]:
            print(f"{group['sha256'][:12]} x{group['count']} {group['reclaimable_bytes']} bytes")
    return 0


def _cmd_storage_dedupe(args: argparse.Namespace) -> int:
    layout = _layout(args)
    result = storage_ops.dedupe(layout.root, apply=args.apply)
    if args.json:
        _json_print(result)
    else:
        print(f"dedupe: replaced={result['replaced']} reclaimable={result['reclaimable_bytes']} bytes apply={result['apply']}")
        for item in result["failed"]:
            print("warning: " + item["path"] + ": " + item["error"])
    return 0


def _cmd_storage_prune(args: argparse.Namespace) -> int:
    layout = _layout(args)
    result = storage_ops.prune(layout.root, apply=args.apply, older_than=args.older_than)
    if args.json:
        _json_print(result)
    else:
        print(f"prune: candidates={len(result['candidates'])} bytes={result['bytes']} removed={result['removed']} apply={result['apply']}")
    return 0


def _cmd_storage_compact(args: argparse.Namespace) -> int:
    layout = _layout(args)
    result = storage_ops.compact(layout.root, apply=args.apply)
    if args.json:
        _json_print(result)
    else:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("ok") else 1


def _cmd_backup_create(args: argparse.Namespace) -> int:
    layout = _layout(args)
    try:
        result = backup_mod.create(
            layout.root, args.out, redact=args.redact, allow_secrets=args.allow_secrets
        )
    except backup_mod.BackupError as exc:
        raise CliError(str(exc)) from None
    if args.json:
        _json_print(result)
    else:
        print(f"backup: {result['path']}")
        print(f"counts: {json.dumps(result['counts'], ensure_ascii=False, sort_keys=True)}")
    return 0


def _cmd_backup_show(args: argparse.Namespace) -> int:
    try:
        result = backup_mod.inspect_bundle(args.bundle)
    except backup_mod.BackupError as exc:
        raise CliError(str(exc)) from None
    if args.json:
        _json_print(result)
    else:
        print(f"backup: {result['path']}")
        print(f"counts: {json.dumps(result['counts'], ensure_ascii=False, sort_keys=True)}")
        print(f"redacted: {result['redacted']}")
    return 0


def _cmd_backup_restore(args: argparse.Namespace) -> int:
    try:
        result = backup_mod.restore_bundle(args.bundle, args.to, apply=args.apply)
    except backup_mod.BackupError as exc:
        raise CliError(str(exc)) from None
    if args.json:
        _json_print(result)
    else:
        print(f"destination: {result['destination']}")
        print(f"dry_run: {result['dry_run']}")
    return 0


def _cmd_backup_inspect(args: argparse.Namespace) -> int:
    layout = _layout(args)
    result = backup_mod.inspect(layout.root)
    if args.json:
        _json_print(result)
    else:
        summary = result["summary"]
        print(f"home: {result['home']}")
        for key in ("assets", "references", "derived", "excluded"):
            item = summary[key]
            print(f"{key:<10} {item['files']:>5} files  {item['bytes']:>10} bytes")
        print(f"secrets    {summary['secrets']['hits']:>5} hits")
        print(f"duplicates {len(result['duplicates']):>5} groups  reclaimable={result['reclaimable_bytes']} bytes")
        for warning in result["warnings"]:
            print("warning: " + warning)
    return 0


def _cmd_export(args: argparse.Namespace) -> int:
    layout = _layout(args)
    result = export_mod.export_home(layout.root, args.out)
    if args.json:
        _json_print(result)
    else:
        print(f"exported: {result['path']}")
        print(f"counts: {json.dumps(result['counts'], ensure_ascii=False, sort_keys=True)}")
    return 0


def _cmd_import(args: argparse.Namespace) -> int:
    destination = Path(args.to).expanduser() if args.to else default_home()
    result = export_mod.import_home(args.file, destination)
    if args.json:
        _json_print(result)
    else:
        print(f"imported: {result['path']}")
        print(f"counts: {json.dumps(result['counts'], ensure_ascii=False, sort_keys=True)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="loomsci")
    parser.add_argument("--home", help="explicit loomsci home")
    parser.add_argument("--url", default=DEFAULT_URL, help="local host URL")
    parser.add_argument("--as", dest="agent", help="agent.owner identity")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="initialize the local workspace")
    init.add_argument("--owner")
    init.add_argument("--agent", default="alice")
    init.add_argument("--json", action="store_true")
    init.set_defaults(func=_cmd_init)

    home = sub.add_parser("home", help="show the resolved home")
    home.add_argument("--json", action="store_true")
    home.set_defaults(func=_cmd_home)

    migrate = sub.add_parser("migrate", help="migrate a legacy home")
    migrate.add_argument("--from", dest="source", required=True, help="legacy home")
    migrate.add_argument("--to", help="destination home (default: ~/.loomsci)")
    migrate.add_argument("--dry-run", action="store_true", help="default; write nothing")
    migrate.add_argument("--apply", action="store_true", help="actually copy files")
    migrate.add_argument("--json", action="store_true")
    migrate.set_defaults(func=_cmd_migrate)

    features = sub.add_parser("features", help="show active profile, routes, jobs, nav")
    features.add_argument("--json", action="store_true")
    features.set_defaults(func=_cmd_features)

    serve = sub.add_parser("serve", help="run the local host")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8787)
    serve.set_defaults(func=_cmd_serve)

    post = sub.add_parser("post", help="create a post")
    post.add_argument("--kind", default="note")
    post.add_argument("--title", default="")
    post.add_argument("--body", required=True)
    post.add_argument("--thread")
    post.add_argument("--parent")
    post.add_argument("--to")
    post.add_argument("--attach", action="append", help="attach a local file")
    post.add_argument("--json", action="store_true")
    post.set_defaults(func=_cmd_post)

    read = sub.add_parser("read", help="read posts since the local cursor")
    read.add_argument("--since", type=int)
    read.add_argument("--thread")
    read.add_argument("--limit", type=int, default=50)
    read.add_argument("--no-update", action="store_true")
    read.add_argument("--json", action="store_true")
    read.set_defaults(func=_cmd_read)

    presence = sub.add_parser("presence", help="register or list IDE presence")
    presence.add_argument("--list", action="store_true")
    presence.add_argument("--tool")
    presence.add_argument("--workspace")
    presence.add_argument("--model")
    presence.add_argument("--pid", type=int)
    presence.add_argument("--json", action="store_true")
    presence.set_defaults(func=_cmd_presence)

    handoff = sub.add_parser("handoff", help="post a structured handoff")
    handoff.add_argument("--task", required=True)
    handoff.add_argument("--to", required=True)
    handoff.add_argument("--completed", action="append")
    handoff.add_argument("--remaining", action="append")
    handoff.add_argument("--next", action="append")
    handoff.add_argument("--risks", action="append")
    handoff.add_argument("--evidence", required=True)
    handoff.add_argument("--json", action="store_true")
    handoff.set_defaults(func=_cmd_handoff)

    agent = sub.add_parser("agent", help="manage additional agents")
    agent_sub = agent.add_subparsers(dest="agent_command", required=True)

    agent_add = agent_sub.add_parser("add", help="add an agent from the baseline")
    agent_add.add_argument("handle")
    agent_add.add_argument("--tool")
    agent_add.add_argument("--role", default="collaborator")
    agent_add.add_argument("--json", action="store_true")
    agent_add.set_defaults(func=_cmd_agent_add)

    agent_list = agent_sub.add_parser("list", help="list local agents")
    agent_list.add_argument("--all", action="store_true", help="include DB-only rows")
    agent_list.add_argument("--json", action="store_true")
    agent_list.set_defaults(func=_cmd_agent_list)

    agent_prune = agent_sub.add_parser("prune", help="remove DB rows without an agent home")
    agent_prune.add_argument("--dry-run", action="store_true", help="only list candidates")
    agent_prune.add_argument("--yes", action="store_true", help="actually delete")
    agent_prune.add_argument("--json", action="store_true")
    agent_prune.set_defaults(func=_cmd_agent_prune)

    task = sub.add_parser("task", help="task lifecycle and leases")
    task_sub = task.add_subparsers(dest="task_command", required=True)

    task_add = task_sub.add_parser("add", help="create a task")
    task_add.add_argument("--title", required=True)
    task_add.add_argument("--description")
    task_add.add_argument("--acceptance")
    task_add.add_argument("--json", action="store_true")
    task_add.set_defaults(func=_cmd_task_add)

    task_list = task_sub.add_parser("list", help="list tasks")
    task_list.add_argument("--status")
    task_list.add_argument("--mine", action="store_true")
    task_list.add_argument("--limit", type=int, default=50)
    task_list.add_argument("--json", action="store_true")
    task_list.set_defaults(func=_cmd_task_list)

    task_claim = task_sub.add_parser("claim", help="claim a task")
    task_claim.add_argument("task_id")
    task_claim.add_argument("--lease", type=int, default=3600)
    task_claim.add_argument("--json", action="store_true")
    task_claim.set_defaults(func=_cmd_task_claim)

    task_done = task_sub.add_parser("done", help="complete a task")
    task_done.add_argument("task_id")
    task_done.add_argument("--evidence", required=True)
    task_done.add_argument("--json", action="store_true")
    task_done.set_defaults(func=_cmd_task_done)

    memory = sub.add_parser("memory", help="project facts and review")
    memory_sub = memory.add_subparsers(dest="memory_command", required=True)

    memory_add = memory_sub.add_parser("add", help="add a candidate fact")
    memory_add.add_argument("--claim", required=True)
    memory_add.add_argument("--evidence")
    memory_add.add_argument("--source")
    memory_add.add_argument("--project")
    memory_add.add_argument("--tags")
    memory_add.add_argument("--confidence", type=float)
    memory_add.add_argument("--json", action="store_true")
    memory_add.set_defaults(func=_cmd_memory_add)

    memory_list = memory_sub.add_parser("list", help="list facts")
    memory_list.add_argument("--q")
    memory_list.add_argument("--status")
    memory_list.add_argument("--project")
    memory_list.add_argument("--limit", type=int, default=50)
    memory_list.add_argument("--json", action="store_true")
    memory_list.set_defaults(func=_cmd_memory_list)

    memory_review = memory_sub.add_parser("review", help="approve/reject a fact")
    memory_review.add_argument("fact_id")
    memory_review.add_argument("--status", choices=["candidate", "approved", "rejected", "archived"], required=True)
    memory_review.add_argument("--json", action="store_true")
    memory_review.set_defaults(func=_cmd_memory_review)

    search = sub.add_parser("search", help="search posts, tasks, and facts")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=50)
    search.add_argument("--json", action="store_true")
    search.set_defaults(func=_cmd_search)

    inbox = sub.add_parser("inbox", help="list or mark mention inbox items")
    inbox.add_argument("--unread", action="store_true")
    inbox.add_argument("--read")
    inbox.add_argument("--read-all", action="store_true")
    inbox.add_argument("--limit", type=int, default=50)
    inbox.add_argument("--json", action="store_true")
    inbox.set_defaults(func=_cmd_inbox)

    watch = sub.add_parser("watch", help="stream new posts")
    watch.add_argument("--since", type=int, default=0)
    watch.add_argument("--once", action="store_true")
    watch.add_argument("--timeout", type=int, default=60)
    watch.add_argument("--json", action="store_true")
    watch.set_defaults(func=_cmd_watch)

    status = sub.add_parser("status", help="show health, integrity, and counts")
    status.add_argument("--json", action="store_true")
    status.set_defaults(func=_cmd_status)

    addon = sub.add_parser("addon", help="local add-on catalog")
    addon_sub = addon.add_subparsers(dest="addon_command", required=True)

    addon_list = addon_sub.add_parser("list", help="list bundled/installed add-ons")
    addon_list.add_argument("--json", action="store_true")
    addon_list.set_defaults(func=_cmd_addon_list)

    addon_install = addon_sub.add_parser("install", help="install a bundled add-on")
    addon_install.add_argument("name")
    addon_install.add_argument("--start", action="store_true", help="start after install")
    addon_install.add_argument("--json", action="store_true")
    addon_install.set_defaults(func=_cmd_addon_install)

    addon_update = addon_sub.add_parser("update", help="update installed add-on code, preserving data")
    addon_update.add_argument("name", nargs="?")
    addon_update.add_argument("--all", action="store_true")
    addon_update.add_argument("--json", action="store_true")
    addon_update.set_defaults(func=_cmd_addon_update)

    addon_verify = addon_sub.add_parser("verify", help="verify installed add-on files and versions")
    addon_verify.add_argument("--json", action="store_true")
    addon_verify.set_defaults(func=_cmd_addon_verify)

    addon_start = addon_sub.add_parser("start", help="start an installed add-on")
    addon_start.add_argument("name", nargs="?")
    addon_start.add_argument("--all", action="store_true")
    addon_start.add_argument("--json", action="store_true")
    addon_start.set_defaults(func=_cmd_addon_start)

    addon_stop = addon_sub.add_parser("stop", help="stop a running add-on")
    addon_stop.add_argument("name", nargs="?")
    addon_stop.add_argument("--all", action="store_true")
    addon_stop.add_argument("--json", action="store_true")
    addon_stop.set_defaults(func=_cmd_addon_stop)

    addon_status = addon_sub.add_parser("status", help="show add-on runtime state")
    addon_status.add_argument("--json", action="store_true")
    addon_status.set_defaults(func=_cmd_addon_status)

    addon_remove = addon_sub.add_parser("remove", help="remove an installed add-on")
    addon_remove.add_argument("name")
    addon_remove.add_argument("--json", action="store_true")
    addon_remove.set_defaults(func=_cmd_addon_remove)

    addon_profile = addon_sub.add_parser("profile", help="install a recommended profile")
    addon_profile.add_argument("profile", choices=sorted(addons_mod.PROFILES))
    addon_profile.add_argument("--start", action="store_true", help="start installed add-ons")
    addon_profile.add_argument("--json", action="store_true")
    addon_profile.set_defaults(func=_cmd_addon_profile)

    storage = sub.add_parser("storage", help="inspect and compact local storage")
    storage_sub = storage.add_subparsers(dest="storage_command", required=True)
    storage_report = storage_sub.add_parser("report", help="read-only storage report")
    storage_report.add_argument("--json", action="store_true")
    storage_report.set_defaults(func=_cmd_storage_report)
    storage_duplicates = storage_sub.add_parser("duplicates", help="list duplicate attachment objects")
    storage_duplicates.add_argument("--json", action="store_true")
    storage_duplicates.set_defaults(func=_cmd_storage_duplicates)
    storage_dedupe = storage_sub.add_parser("dedupe", help="hardlink duplicate attachment blobs")
    storage_dedupe.add_argument("--apply", action="store_true")
    storage_dedupe.add_argument("--json", action="store_true")
    storage_dedupe.set_defaults(func=_cmd_storage_dedupe)
    storage_prune = storage_sub.add_parser("prune", help="remove old orphan blobs")
    storage_prune.add_argument("--apply", action="store_true")
    storage_prune.add_argument("--older-than", type=int, default=3600)
    storage_prune.add_argument("--json", action="store_true")
    storage_prune.set_defaults(func=_cmd_storage_prune)
    storage_compact = storage_sub.add_parser("compact", help="checkpoint WAL and VACUUM")
    storage_compact.add_argument("--apply", action="store_true")
    storage_compact.add_argument("--json", action="store_true")
    storage_compact.set_defaults(func=_cmd_storage_compact)

    backup = sub.add_parser("backup", help="inspect backup asset boundaries")
    backup_sub = backup.add_subparsers(dest="backup_command", required=True)
    backup_inspect = backup_sub.add_parser("inspect", help="read-only asset/secret inventory")
    backup_inspect.add_argument("--json", action="store_true")
    backup_inspect.set_defaults(func=_cmd_backup_inspect)

    backup_create = backup_sub.add_parser("create", help="create a portable asset bundle")
    backup_create.add_argument("--out", required=True)
    backup_create.add_argument("--redact", action="store_true")
    backup_create.add_argument("--allow-secrets", action="store_true")
    backup_create.add_argument("--json", action="store_true")
    backup_create.set_defaults(func=_cmd_backup_create)

    backup_show = backup_sub.add_parser("show", help="verify and summarize a bundle")
    backup_show.add_argument("bundle")
    backup_show.add_argument("--json", action="store_true")
    backup_show.set_defaults(func=_cmd_backup_show)

    backup_restore = backup_sub.add_parser("restore", help="dry-run or restore a bundle")
    backup_restore.add_argument("bundle")
    backup_restore.add_argument("--to", required=True)
    backup_restore.add_argument("--apply", action="store_true", help="write to an empty destination")
    backup_restore.add_argument("--json", action="store_true")
    backup_restore.set_defaults(func=_cmd_backup_restore)

    export = sub.add_parser("export", help="export the home as a zip")
    export.add_argument("--out", required=True)
    export.add_argument("--json", action="store_true")
    export.set_defaults(func=_cmd_export)

    import_cmd = sub.add_parser("import", help="import an export zip")
    import_cmd.add_argument("file")
    import_cmd.add_argument("--to")
    import_cmd.add_argument("--json", action="store_true")
    import_cmd.set_defaults(func=_cmd_import)

    alice = sub.add_parser("alice", help="manage the default agent baseline")
    alice_sub = alice.add_subparsers(dest="alice_command", required=True)

    alice_init = alice_sub.add_parser("init", help="create the default agent")
    alice_init.add_argument("--owner", required=True)
    alice_init.add_argument("--short", default="alice")
    alice_init.add_argument("--json", action="store_true")
    alice_init.set_defaults(func=_cmd_alice_init)

    alice_show = alice_sub.add_parser("show", help="show the agent record")
    alice_show.add_argument("--short", default="alice")
    alice_show.add_argument("--json", action="store_true")
    alice_show.set_defaults(func=_cmd_alice_show)

    alice_review = alice_sub.add_parser("review", help="show persona snapshots")
    alice_review.add_argument("--short", default="alice")
    alice_review.add_argument("--json", action="store_true")
    alice_review.set_defaults(func=_cmd_alice_review)

    alice_snapshot = alice_sub.add_parser("snapshot", help="snapshot persona")
    alice_snapshot.add_argument("--short", default="alice")
    alice_snapshot.add_argument("--reason", default="manual")
    alice_snapshot.add_argument("--json", action="store_true")
    alice_snapshot.set_defaults(func=_cmd_alice_snapshot)

    alice_reset = alice_sub.add_parser("reset", help="restore the baseline")
    alice_reset.add_argument("--short", default="alice")
    alice_reset.add_argument("--drop-memory", action="store_true")
    alice_reset.add_argument("--json", action="store_true")
    alice_reset.set_defaults(func=_cmd_alice_reset)

    alice_rename = alice_sub.add_parser("rename", help="rename the agent")
    alice_rename.add_argument("--short", default="alice")
    alice_rename.add_argument("--to", required=True)
    alice_rename.add_argument("--owner")
    alice_rename.add_argument("--json", action="store_true")
    alice_rename.set_defaults(func=_cmd_alice_rename)
    return parser


def _hoist_global_options(argv: list[str]) -> list[str]:
    """Allow --as/--url/--home after the subcommand."""
    head: list[str] = []
    rest: list[str] = []
    index = 0
    names = {"--as", "--url", "--home"}
    while index < len(argv):
        arg = argv[index]
        if arg in names and index + 1 < len(argv):
            head.extend([arg, argv[index + 1]])
            index += 2
            continue
        if any(arg.startswith(name + "=") for name in names):
            head.append(arg)
            index += 1
            continue
        rest.append(arg)
        index += 1
    return head + rest


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    raw = list(sys.argv[1:] if argv is None else argv)
    args = parser.parse_args(_hoist_global_options(raw))
    if getattr(args, "apply", False) and getattr(args, "dry_run", False):
        parser.error("--apply and --dry-run are mutually exclusive")
    try:
        return int(args.func(args))
    except (HomeError, CliError, export_mod.ExportError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
