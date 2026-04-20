#!/usr/bin/env bash
set -euo pipefail

TMP_SITE_DIR=".mkdocs-site-tmp"
OUT_SITE_DIR="docs/site"
LEGACY_SITE_DIR="site"
BUILD_MODULE="scripts.docs.build.mkdocs_build"

STRICT_FLAG=""
if [[ "${1:-}" == "--strict" ]]; then
  STRICT_FLAG="--strict"
fi

cleanup_tmp() {
  if [[ -d "$TMP_SITE_DIR" ]]; then
    rm -rf "$TMP_SITE_DIR"
  fi
  return 0
}

trap cleanup_tmp EXIT

if python -c "import mkdocs" >/dev/null 2>&1; then
  python -m "$BUILD_MODULE" $STRICT_FLAG --clean --site-dir "$TMP_SITE_DIR"
elif [[ -x "./.venv/bin/python" ]]; then
  ./.venv/bin/python -m "$BUILD_MODULE" $STRICT_FLAG --clean --site-dir "$TMP_SITE_DIR"
elif [[ -x "./.venv/Scripts/python.exe" ]]; then
  # WSL can fail executing Windows binaries directly depending on interop policy.
  if command -v cmd.exe >/dev/null 2>&1 && command -v wslpath >/dev/null 2>&1; then
    WIN_REPO_ROOT="$(wslpath -w "$PWD")"
    cmd.exe /c "cd /d \"$WIN_REPO_ROOT\" && .venv\\Scripts\\python.exe -m $BUILD_MODULE $STRICT_FLAG --clean --site-dir \"$TMP_SITE_DIR\""
  else
    ./.venv/Scripts/python.exe -m "$BUILD_MODULE" $STRICT_FLAG --clean --site-dir "$TMP_SITE_DIR"
  fi
else
  mkdocs build $STRICT_FLAG --clean --site-dir "$TMP_SITE_DIR"
fi

rm -rf "$OUT_SITE_DIR"
mkdir -p "$(dirname "$OUT_SITE_DIR")"
if ! mv "$TMP_SITE_DIR" "$OUT_SITE_DIR"; then
  mkdir -p "$OUT_SITE_DIR"
  cp -a "$TMP_SITE_DIR"/. "$OUT_SITE_DIR"/
  rm -rf "$TMP_SITE_DIR"
fi

# Normalize generated artifacts to a single location.
rm -rf "$LEGACY_SITE_DIR"

trap - EXIT
echo "MkDocs site generated at $OUT_SITE_DIR"
