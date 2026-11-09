"""loomsci command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

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
from core.local_auth import is_loopback_host
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


def _cmd_serve(args: argparse.Namespace) -> int:
    if not is_loopback_host(args.host):
        print("error: the Core profile only binds a loopback host", file=sys.stderr)
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
    payload = {
        "kind": args.kind,
        "title": args.title or "",
        "body": args.body,
        "thread_id": args.thread,
        "parent_id": args.parent,
        "meta": {"to": args.to} if args.to else {},
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
            print(
                f"{post.get('seq')} {post.get('id')} {post.get('author')} "
                f"{post.get('kind')} {post.get('title') or ''}".rstrip()
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


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "apply", False) and getattr(args, "dry_run", False):
        parser.error("--apply and --dry-run are mutually exclusive")
    try:
        return int(args.func(args))
    except (HomeError, CliError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
