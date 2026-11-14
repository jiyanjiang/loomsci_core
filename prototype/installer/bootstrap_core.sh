#!/bin/sh
# No-Python bootstrap for a signed Core package. Not product code.
# Usage: bootstrap_core.sh --package DIR --home DIR --trust DIR --uv PATH --sha256 FILE

set -eu
PACKAGE=""; HOME_DIR=""; TRUST=""; UV=""; SHA=""; PY_DIR=""
while [ $# -gt 0 ]; do
  case "$1" in
    --package) PACKAGE="$2"; shift 2 ;;
    --home) HOME_DIR="$2"; shift 2 ;;
    --trust) TRUST="$2"; shift 2 ;;
    --uv) UV="$2"; shift 2 ;;
    --sha256) SHA="$2"; shift 2 ;;
    --python-dir) PY_DIR="$2"; shift 2 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done
[ -n "$PACKAGE" ] && [ -n "$HOME_DIR" ] && [ -n "$TRUST" ] && [ -n "$UV" ] && [ -n "$SHA" ] || {
  echo "package, home, trust, uv, sha256 are required" >&2; exit 2;
}
EXPECTED=$(awk '{print $1}' "$SHA")
ACTUAL=$(shasum -a 256 "$UV" | awk '{print $1}')
[ "$EXPECTED" = "$ACTUAL" ] || { echo "uv_checksum_mismatch" >&2; exit 1; }

WORK="$HOME_DIR.bootstrap-$$"
trap 'rm -rf "$WORK"' EXIT
mkdir -p "$WORK"
mkdir -p "$HOME_DIR/runtime/python"
if [ -n "$PY_DIR" ]; then
  export UV_PYTHON_INSTALL_DIR="$PY_DIR"
else
  export UV_PYTHON_INSTALL_DIR="$HOME_DIR/runtime/python"
  "$UV" python install 3.12 --managed-python --install-dir "$HOME_DIR/runtime/python"
fi
"$UV" venv --managed-python --python 3.12 "$WORK/venv"
"$UV" pip install --python "$WORK/venv/bin/python" cryptography >/dev/null
$WORK/venv/bin/python "$(dirname "$0")/install_core.py" \
  --package "$PACKAGE" --home "$HOME_DIR" --trust "$TRUST" --uv "$UV"
