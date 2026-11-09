#!/usr/bin/env python3
"""Point this clone at the versioned Git hooks in .githooks/."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    try:
        subprocess.run(
            ["git", "config", "core.hooksPath", ".githooks"],
            cwd=ROOT,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"failed to install hooks: {exc}", file=sys.stderr)
        return 1
    print("installed: core.hooksPath=.githooks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
