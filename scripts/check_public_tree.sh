#!/usr/bin/env bash
# macOS/Linux wrapper. Windows users should run:
#   python scripts\check_public_tree.py
set -euo pipefail
cd "$(dirname "$0")/.."
exec python3 scripts/check_public_tree.py
