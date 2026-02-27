#!/usr/bin/env bash
set -euo pipefail

DOCS_DIR="${1:-docs}"
ERRORS=0

have_cmd() {
  command -v "$1" >/dev/null 2>&1
}

err() {
  echo "ERROR: $*"
  ERRORS=$((ERRORS + 1))
}

while IFS= read -r -d '' file; do
  if ! grep -Eq '%%\{\s*(init|initialize)\s*:' "$file"; then
    err "Missing init: $file"
  fi

  if ! grep -Eq '^\s*%%\s*View\s*:' "$file"; then
    err "Missing View meta: $file"
  fi

  if have_cmd mmdc; then
    if ! mmdc -i "$file" -o /tmp/_check.png >/dev/null 2>&1; then
      err "mmdc failed: $file"
    fi
  fi
done < <(find "$DOCS_DIR" -type f \( -name "*.mmd" -o -name "*.mermaid" \) -print0)

while IFS= read -r -d '' file; do
  stem="${file%.*}"
  if [[ ! -f "${stem}.mmd" && ! -f "${stem}.mermaid" && ! -f "${stem}.puml" && ! -f "${stem}.d2" && ! -f "${stem}.meta" ]]; then
    err "Raster/vector without source: $file"
  fi
done < <(find "$DOCS_DIR" -type f \( -name "*.png" -o -name "*.svg" \) -print0)

if [[ "$ERRORS" -gt 0 ]]; then
  echo "Validation failed: $ERRORS issue(s) detected."
  exit 1
fi

echo "Validation passed: no policy violations found."
