#!/bin/sh
# Minimal uv runtime bootstrap prototype. Not product code.
# Usage: LOOMSCI_UV=/path/to/uv ./bootstrap.sh [--home DIR] [--offline]

set -eu

HOME_DIR="${LOOMSCI_HOME:-$HOME/.loomsci}"
OFFLINE=0
while [ $# -gt 0 ]; do
  case "$1" in
    --home) HOME_DIR="$2"; shift 2 ;;
    --offline) OFFLINE=1; shift ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

UV="${LOOMSCI_UV:-$(command -v uv 2>/dev/null || true)}"
if [ -z "$UV" ] || [ ! -x "$UV" ]; then
  if [ "$OFFLINE" = "1" ]; then
    echo "uv_missing: offline mode requires LOOMSCI_UV" >&2
    exit 1
  fi
  echo "uv_missing: production installer must download a pinned uv binary" >&2
  echo "set LOOMSCI_UV or install uv first (prototype uses existing uv)" >&2
  exit 1
fi

mkdir -p "$HOME_DIR/runtime/python" "$HOME_DIR/venv"
export UV_PYTHON_INSTALL_DIR="$HOME_DIR/runtime/python"
if [ "$OFFLINE" = "1" ]; then export UV_PYTHON_DOWNLOADS=never; fi

"$UV" python install 3.12 --managed-python --install-dir "$HOME_DIR/runtime/python"
"$UV" venv --allow-existing --managed-python --python 3.12 "$HOME_DIR/venv"

PY="$HOME_DIR/venv/bin/python"
if [ ! -x "$PY" ]; then
  echo "venv_python_missing: $PY" >&2
  exit 1
fi

VERSION="$("$PY" -c 'import sys; print(".".join(map(str, sys.version_info[:3])))')"
UV_VERSION="$("$UV" --version | awk '{print $2}')"
cat > "$HOME_DIR/runtime.json" <<EOF
{
  "runtime": "python",
  "python": "$PY",
  "version": "$VERSION",
  "uv": "$UV_VERSION",
  "home": "$HOME_DIR",
  "offline": $OFFLINE
}
EOF
printf '%s\n' "runtime: $VERSION"
printf '%s\n' "python:  $PY"
printf '%s\n' "uv:      $UV_VERSION"
