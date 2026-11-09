#!/usr/bin/env bash
# loomsci_core installer (macOS / Linux).
set -euo pipefail

PACKAGE=""
HOME_DIR="${LOOMSCI_HOME:-$HOME/.loomsci}"
NO_DEPS="0"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --package) PACKAGE="$2"; shift 2 ;;
    --home) HOME_DIR="$2"; shift 2 ;;
    --no-deps) NO_DEPS="1"; shift ;;
    -h|--help)
      echo "usage: install.sh [--package FILE.zip] [--home DIR] [--no-deps]"
      exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

if [[ -n "$PACKAGE" ]]; then
  [[ -f "$PACKAGE" ]] || { echo "package not found: $PACKAGE" >&2; exit 2; }
  command -v unzip >/dev/null || { echo "unzip is required" >&2; exit 2; }
  unzip -q "$PACKAGE" -d "$TMP"
  SOURCE="$(find "$TMP" -maxdepth 2 -name pyproject.toml -print -quit | xargs dirname)"
else
  SOURCE="$(cd "$(dirname "$0")" && pwd)"
fi
[[ -f "$SOURCE/pyproject.toml" ]] || { echo "package root not found" >&2; exit 2; }

mkdir -p "$HOME_DIR/bin" "$HOME_DIR/data" "$HOME_DIR/agents" \
         "$HOME_DIR/packs" "$HOME_DIR/logs" "$HOME_DIR/runtime"
VENV="$HOME_DIR/venv"
if [[ ! -x "$VENV/bin/python" ]]; then
  PYTHON_BIN="${LOOMSCI_PYTHON:-python3.12}"
  "$PYTHON_BIN" -m venv "$VENV"
fi

rm -rf "$HOME_DIR/core.new"
mkdir -p "$HOME_DIR/core.new"
for item in core cli presets docs scripts pyproject.toml requirements.txt \
            VERSION README.md README.zh-CN.md LICENSE NOTICE SECURITY.md \
            CONTRIBUTING.md AGENTS.md BUILD_INFO.json upgrade-manifest.json; do
  if [[ -e "$SOURCE/$item" ]]; then
    cp -R "$SOURCE/$item" "$HOME_DIR/core.new/"
  fi
done

if [[ "$NO_DEPS" != "1" ]]; then
  "$VENV/bin/python" -m pip install --disable-pip-version-check -r "$HOME_DIR/core.new/requirements.txt"
fi

if [[ -d "$HOME_DIR/core" ]]; then
  rm -rf "$HOME_DIR/core.prev"
  mv "$HOME_DIR/core" "$HOME_DIR/core.prev"
fi
mv "$HOME_DIR/core.new" "$HOME_DIR/core"

cat > "$HOME_DIR/bin/loomsci" <<EOF
#!/usr/bin/env sh
exec env PYTHONPATH="$HOME_DIR/core" LOOMSCI_HOME="$HOME_DIR" "$VENV/bin/python" -m cli.loomsci "\$@"
EOF
chmod +x "$HOME_DIR/bin/loomsci"

echo "installed: $HOME_DIR/core"
echo "launcher:  $HOME_DIR/bin/loomsci"
echo "next:      $HOME_DIR/bin/loomsci alice init --owner <name>"
