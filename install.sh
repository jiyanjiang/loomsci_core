#!/usr/bin/env bash
# loomsci_core installer (macOS / Linux).
set -euo pipefail

PACKAGE=""
HOME_DIR="${LOOMSCI_HOME:-$HOME/.loomsci}"
NO_DEPS="0"
FROM_RELEASE="0"
DRY_RUN="0"
RELEASE_BASE="${LOOMSCI_RELEASE_BASE:-https://raw.githubusercontent.com/jiyanjiang/loomsci_core/main}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --package) PACKAGE="$2"; shift 2 ;;
    --home) HOME_DIR="$2"; shift 2 ;;
    --no-deps) NO_DEPS="1"; shift ;;
    --from-release) FROM_RELEASE="1"; shift ;;
    --release-base) RELEASE_BASE="$2"; shift 2 ;;
    --dry-run) DRY_RUN="1"; shift ;;
    -h|--help)
      echo "usage: install.sh [--package FILE.zip | --from-release] [--release-base URL] [--home DIR] [--no-deps] [--dry-run]"
      exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

if [[ "$FROM_RELEASE" = "1" && -n "$PACKAGE" ]]; then
  echo "use either --package or --from-release" >&2; exit 2
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

if [[ "$FROM_RELEASE" = "1" ]]; then
  command -v curl >/dev/null || { echo "curl is required for --from-release" >&2; exit 2; }
  MANIFEST_URL="${RELEASE_BASE%/}/release-manifest.json"
  MANIFEST_JSON="$(curl -fsSL "$MANIFEST_URL")" || { echo "cannot read $MANIFEST_URL" >&2; exit 2; }
  field() {
    printf '%s' "$MANIFEST_JSON" | tr -d '\r' \
      | sed -n "s/.*\"$1\"[[:space:]]*:[[:space:]]*\"\([^\"]*\)\".*/\1/p" | head -1
  }
  VERSION="$(field version)"
  FILE="$(field file)"
  EXPECTED="$(field sha256)"
  [[ -n "$VERSION" && -n "$FILE" && -n "$EXPECTED" ]] || { echo "invalid release manifest" >&2; exit 2; }
  URL="${RELEASE_BASE%/}/releases/$FILE"
  if [[ "$DRY_RUN" = "1" ]]; then
    echo "version: $VERSION"
    echo "url:     $URL"
    echo "sha256:  $EXPECTED"
    exit 0
  fi
  command -v unzip >/dev/null || { echo "unzip is required" >&2; exit 2; }
  PACKAGE="$TMP/package.zip"
  curl -fL --retry 3 --connect-timeout 10 --max-time 300 "$URL" -o "$PACKAGE" || { echo "download failed" >&2; exit 2; }
  ACTUAL="$(shasum -a 256 "$PACKAGE" | awk '{print $1}')"
  if [[ "$ACTUAL" != "$EXPECTED" ]]; then
    echo "package SHA256 mismatch" >&2
    echo "  expected: $EXPECTED" >&2
    echo "  actual:   $ACTUAL" >&2
    exit 3
  fi
fi

if [[ "$DRY_RUN" = "1" ]]; then
  echo "package: ${PACKAGE:-$PWD}"
  exit 0
fi

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
chmod 700 "$HOME_DIR" "$HOME_DIR/data" "$HOME_DIR/agents" \
          "$HOME_DIR/packs" "$HOME_DIR/logs" "$HOME_DIR/runtime" 2>/dev/null || true
VENV="$HOME_DIR/venv"
if [[ ! -x "$VENV/bin/python" ]]; then
  PYTHON_BIN="${LOOMSCI_PYTHON:-python3.12}"
  "$PYTHON_BIN" -m venv "$VENV"
fi

rm -rf "$HOME_DIR/core.new"
mkdir -p "$HOME_DIR/core.new"
for item in core cli presets addons docs scripts pyproject.toml requirements.txt \
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
exec env PYTHONPATH="$HOME_DIR/core" PYTHONSAFEPATH=1 LOOMSCI_HOME="$HOME_DIR" "$VENV/bin/python" -m cli.loomsci "\$@"
EOF
chmod +x "$HOME_DIR/bin/loomsci"

echo "installed: $HOME_DIR/core"
echo "launcher:  $HOME_DIR/bin/loomsci"
echo "next:      $HOME_DIR/bin/loomsci alice init --owner <name>"
echo "then:      $HOME_DIR/bin/loomsci doctor"
echo "start:     $HOME_DIR/bin/loomsci up"
