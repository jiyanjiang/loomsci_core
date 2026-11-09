"""Minimal loomsci CLI for the S1 home slice."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from core.home import (
    HomeError,
    apply_migration,
    default_home,
    migration_plan,
    resolve_home,
)
from core.packs import Registry


def _json_print(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="loomsci")
    parser.add_argument("--home", help="explicit loomsci home")
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
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "apply", False) and getattr(args, "dry_run", False):
        parser.error("--apply and --dry-run are mutually exclusive")
    try:
        return int(args.func(args))
    except HomeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
