#!/usr/bin/env python3
"""List bug reports and enforce the batch-fix threshold."""

from __future__ import annotations

import argparse
import datetime as _dt
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
BUGS = ROOT / "bugs"
THRESHOLD = 10
STATUSES = {"open", "in-progress", "fixed", "closed", "blocked"}


def _report_paths(root: Path) -> list[Path]:
    return sorted(path for path in root.glob("[0-9][0-9][0-9][0-9]-*.md"))


def load_reports(root: Path = BUGS) -> list[dict]:
    reports = []
    for path in _report_paths(root):
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---\n"):
            continue
        _, front_matter, _ = text.split("---", 2)
        meta = yaml.safe_load(front_matter) or {}
        if not isinstance(meta, dict):
            continue
        meta["path"] = path
        reports.append(meta)
    return reports


def open_reports(root: Path = BUGS) -> list[dict]:
    return [report for report in load_reports(root) if report.get("status") == "open"]


def gate(root: Path = BUGS, threshold: int = THRESHOLD) -> tuple[int, int]:
    count = len(open_reports(root))
    return count, int(count >= threshold)


def _slug(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:60] or "bug"


def add_report(title: str, surface: str, severity: str, root: Path = BUGS) -> Path:
    if severity not in {"P0", "P1", "P2", "P3"}:
        raise ValueError(f"unknown severity: {severity}")
    root.mkdir(parents=True, exist_ok=True)
    existing = _report_paths(root)
    next_id = 1
    if existing:
        next_id = max(int(path.name[:4]) for path in existing) + 1
    bug_id = f"BUG-{next_id:04d}"
    path = root / f"{next_id:04d}-{_slug(title)}.md"
    path.write_text(
        "---\n"
        f"id: {bug_id}\n"
        f"title: {title}\n"
        "status: open\n"
        f"severity: {severity}\n"
        f"surface: {surface}\n"
        f"reported: {_dt.date.today().isoformat()}\n"
        "---\n\n"
        f"# {bug_id} · {title}\n\n"
        "## Reproduction\n\n"
        "## Expected\n\n"
        "## Actual\n\n"
        "## Evidence\n\n"
        "## Root cause\n\n"
        "## Fix scope\n\n"
        f"Open. Count: {len(open_reports(root)) + 1}/{THRESHOLD}.\n",
        encoding="utf-8",
    )
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=BUGS, help="bug report directory")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="print every report")
    sub.add_parser("status", help="print open count and threshold state")
    sub.add_parser("gate", help="exit 0 only when the batch threshold is met")

    new = sub.add_parser("new", help="create one report")
    new.add_argument("--title", required=True)
    new.add_argument("--surface", default="unclassified")
    new.add_argument("--severity", default="P2", choices=["P0", "P1", "P2", "P3"])

    args = parser.parse_args(argv)
    if args.command == "new":
        path = add_report(args.title, args.surface, args.severity, args.root)
        try:
            print(path.relative_to(ROOT))
        except ValueError:
            print(path)
        return 0

    reports = load_reports(args.root)
    if args.command == "list":
        for report in reports:
            print(
                f"{report.get('id', '?'):8} "
                f"{report.get('severity', '?'):2} "
                f"{report.get('status', '?'):11} "
                f"{report.get('title', '')}"
            )
        return 0

    count, ready = gate(args.root)
    print(f"open bugs: {count}/{THRESHOLD}")
    print("READY: threshold reached" if ready else "BLOCKED: keep collecting reports")
    return 0 if ready else 1


if __name__ == "__main__":
    sys.exit(main())
