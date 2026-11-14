#!/bin/sh
# uv-less installer prototype. Not product code.
# Usage: ./install.sh --home DIR --uv PATH --sha256 FILE [--offline]
# Requires no uv/python on PATH; uses the explicit uv binary.

set -eu

HOME_DIR="${LOOMSCI_HOME:-$HOME/.loomsci}"
UV=""
SHA=""
OFFLINE=0
while [ $# -gt 0 ]; do
  case "$1" in
    --home) HOME_DIR="$2"; shift 2 ;;
    --uv) UV="$2"; shift 2 ;;
    --sha256) SHA="$2"; shift 2 ;;
    --offline) OFFLINE=1; shift ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done
[ -n "$UV" ] || { echo "uv_required" >&2; exit 2; }
[ -n "$SHA" ] || { echo "sha256_required" >&2; exit 2; }
[ -x "$UV" ] || { echo "uv_not_executable: $UV" >&2; exit 2; }
[ -f "$SHA" ] || { echo "sha256_file_missing: $SHA" >&2; exit 2; }

EXPECTED=$(awk '{print $1}' "$SHA")
ACTUAL=$(shasum -a 256 "$UV" | awk '{print $1}')
[ "$EXPECTED" = "$ACTUAL" ] || { echo "uv_checksum_mismatch" >&2; exit 1; }

mkdir -p "$HOME_DIR/runtime/python" "$HOME_DIR/venv"
export UV_PYTHON_INSTALL_DIR="$HOME_DIR/runtime/python"
if [ "$OFFLINE" = "1" ]; then export UV_PYTHON_DOWNLOADS=never; fi

"$UV" python install 3.12 --managed-python --install-dir "$HOME_DIR/runtime/python"
"$UV" venv --allow-existing --managed-python --python 3.12 "$HOME_DIR/venv"
PY="$HOME_DIR/venv/bin/python"
[ -x "$PY" ] || { echo "venv_python_missing: $PY" >&2; exit 1; }
VERSION=$("$PY" --version | sed 's/^Python //')
UV_VERSION=$("$UV" --version | awk '{print $2}')
cat > "$HOME_DIR/install.json" <<EOF
{
  "format": "loomsci-install/1",
  "home": "$HOME_DIR",
  "python": "$PY",
  "python_version": "$VERSION",
  "uv": "$UV_VERSION",
  "uv_sha256": "$ACTUAL",
  "offline": $OFFLINE
}
EOF
printf '%s\n' "install: $VERSION"
printf '%s\n' "python:  $PY"
printf '%s\n' "uv:      $UV_VERSION"
