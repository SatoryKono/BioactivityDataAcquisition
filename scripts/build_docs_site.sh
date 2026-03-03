#!/usr/bin/env bash
set -euo pipefail

TMP_SITE_DIR=".mkdocs-site-tmp"
OUT_SITE_DIR="docs/site"

STRICT_FLAG=""
if [[ "${1:-}" == "--strict" ]]; then
  STRICT_FLAG="--strict"
fi

cleanup_tmp() {
  if [[ -d "$TMP_SITE_DIR" ]]; then
    rm -rf "$TMP_SITE_DIR"
  fi
}

trap cleanup_tmp EXIT

if command -v mkdocs >/dev/null 2>&1; then
  MKDOCS_CMD=(mkdocs)
elif [[ -x "./.venv/Scripts/python.exe" ]]; then
  MKDOCS_CMD=("./.venv/Scripts/python.exe" -m mkdocs)
elif [[ -x "./.venv/bin/python" ]]; then
  MKDOCS_CMD=("./.venv/bin/python" -m mkdocs)
else
  MKDOCS_CMD=(python -m mkdocs)
fi

"${MKDOCS_CMD[@]}" build $STRICT_FLAG --clean --site-dir "$TMP_SITE_DIR"

rm -rf "$OUT_SITE_DIR"
mkdir -p "$(dirname "$OUT_SITE_DIR")"
mv "$TMP_SITE_DIR" "$OUT_SITE_DIR"

trap - EXIT
echo "MkDocs site generated at $OUT_SITE_DIR"
