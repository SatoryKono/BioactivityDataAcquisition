#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOCS_ROOT="$REPO_ROOT/docs"
THEME_CONFIG="$REPO_ROOT/docs/02-architecture/mmd-diagrams/theme/mermaid-config.json"
PUPPETEER_CFG=""

usage() {
  cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Validate all Mermaid source files in docs/:
  - includes: docs/**/*.mmd, docs/**/*.mermaid
  - excludes: docs/99-archive/**

Options:
  --docs-root DIR     Docs root directory (default: $DOCS_ROOT)
  --puppeteer FILE    Puppeteer config JSON path
  -h, --help          Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --docs-root)
      [[ $# -ge 2 ]] || { echo "Missing value for $1" >&2; exit 2; }
      DOCS_ROOT="$2"
      shift 2
      ;;
    --puppeteer)
      [[ $# -ge 2 ]] || { echo "Missing value for $1" >&2; exit 2; }
      PUPPETEER_CFG="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 2
      ;;
  esac
done

if ! command -v mmdc >/dev/null 2>&1; then
  echo "Error: mmdc not found. Install with: npm install -g @mermaid-js/mermaid-cli" >&2
  exit 2
fi

if [[ "$DOCS_ROOT" != /* ]]; then
  DOCS_ROOT="$REPO_ROOT/$DOCS_ROOT"
fi

if [[ ! -d "$DOCS_ROOT" ]]; then
  echo "Error: docs root does not exist: $DOCS_ROOT" >&2
  exit 2
fi

tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT

count=0
failed=0
mmdc_args=()
if [[ -f "$THEME_CONFIG" ]]; then
  mmdc_args+=(-c "$THEME_CONFIG")
fi
if [[ -n "$PUPPETEER_CFG" ]]; then
  mmdc_args+=(-p "$PUPPETEER_CFG")
fi

while IFS= read -r -d '' file; do
  base="$(basename "${file%.*}")"
  [[ "$base" = _* ]] && continue
  count=$((count + 1))
  out="$tmp_dir/${base}.svg"
  err="$tmp_dir/${base}.err"
  echo "Validating $file"
  if ! mmdc -i "$file" -o "$out" "${mmdc_args[@]}" >/dev/null 2>"$err"; then
    echo "ERROR: Mermaid validation failed for $file" >&2
    if grep -q "Could not find Chrome" "$err"; then
      echo "HINT: mmdc could not find Chrome/Chromium for Puppeteer." >&2
      echo "      Install browser runtime: npx puppeteer browsers install chrome-headless-shell" >&2
      echo "      Or provide --puppeteer <config.json> with executablePath/args." >&2
    fi
    if [[ -s "$err" ]]; then
      echo "DETAILS:" >&2
      sed -n '1,6p' "$err" >&2
    fi
    failed=$((failed + 1))
  fi
done < <(find "$DOCS_ROOT" -type f \( -name "*.mermaid" -o -name "*.mmd" \) \
  -not -path "$DOCS_ROOT/99-archive/*" -print0)

if [[ "$failed" -gt 0 ]]; then
  echo "Validation failed: $failed of $count diagram(s) failed." >&2
  exit 1
fi

echo "Validation passed: $count diagram(s) checked."
