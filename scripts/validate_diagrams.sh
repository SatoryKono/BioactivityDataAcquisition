#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOCS_ROOT="$REPO_ROOT/docs"
RUN_SMOKE=0

usage() {
  cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Validate docs diagrams:
  1) Mermaid headers: %%{init ...}%% and %% View:
  2) Source policy for PNG/SVG: matching .mmd/.mermaid/.puml/.d2/.meta
  3) Optional smoke-render for Mermaid sources if mmdc exists

Options:
  --docs-root DIR    Docs root (default: $DOCS_ROOT)
  --smoke-render     Run mmdc smoke render if binary exists
  -h, --help         Show this help

Exit codes:
  0 = all checks passed
  1 = policy violations found
  2 = usage or environment error
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --docs-root)
      [[ $# -ge 2 ]] || { echo "Missing value for $1" >&2; exit 2; }
      DOCS_ROOT="$2"
      shift 2
      ;;
    --smoke-render)
      RUN_SMOKE=1
      shift
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

if [[ "$DOCS_ROOT" != /* ]]; then
  DOCS_ROOT="$REPO_ROOT/$DOCS_ROOT"
fi

if [[ ! -d "$DOCS_ROOT" ]]; then
  echo "docs root does not exist: $DOCS_ROOT" >&2
  exit 2
fi

violations=0
checked_mermaid=0
checked_images=0

check_mermaid_metadata() {
  local file="$1"
  checked_mermaid=$((checked_mermaid + 1))

  if ! grep -qE '^%%\{init.*\}%%' "$file"; then
    echo "[META] missing init header: $file" >&2
    violations=$((violations + 1))
  fi

  if ! grep -q '^%% View:' "$file"; then
    echo "[META] missing View metadata: $file" >&2
    violations=$((violations + 1))
  fi
}

has_source_pair() {
  local image="$1"
  local dir stem parent
  dir="$(dirname "$image")"
  stem="$(basename "${image%.*}")"
  parent="$(dirname "$dir")"

  local exts=(".mmd" ".mermaid" ".puml" ".d2" ".meta")
  local ext
  for ext in "${exts[@]}"; do
    [[ -f "$dir/$stem$ext" ]] && return 0
    [[ -f "$parent/$stem$ext" ]] && return 0
  done
  return 1
}

while IFS= read -r -d '' src; do
  base="$(basename "${src%.*}")"
  [[ "$base" = _* ]] && continue
  check_mermaid_metadata "$src"
done < <(find "$DOCS_ROOT" -type f \( -name "*.mmd" -o -name "*.mermaid" \) -not -path "$DOCS_ROOT/99-archive/*" -print0)

while IFS= read -r -d '' img; do
  checked_images=$((checked_images + 1))
  if ! has_source_pair "$img"; then
    echo "[SOURCE] no source pair for image: $img" >&2
    violations=$((violations + 1))
  fi
done < <(find "$DOCS_ROOT" -type f \( -name "*.svg" -o -name "*.png" \) -not -path "$DOCS_ROOT/99-archive/*" -print0)

if [[ "$RUN_SMOKE" -eq 1 ]]; then
  if command -v mmdc >/dev/null 2>&1; then
    tmp_dir="$(mktemp -d)"
    trap 'rm -rf "$tmp_dir"' EXIT
    while IFS= read -r -d '' src; do
      base="$(basename "${src%.*}")"
      [[ "$base" = _* ]] && continue
      out="$tmp_dir/$base.svg"
      if ! mmdc -i "$src" -o "$out" >/dev/null 2>"$tmp_dir/mmdc.err"; then
        echo "[SMOKE] mmdc failed: $src" >&2
        sed -n '1,5p' "$tmp_dir/mmdc.err" >&2 || true
        violations=$((violations + 1))
      fi
    done < <(find "$DOCS_ROOT" -type f \( -name "*.mmd" -o -name "*.mermaid" \) -not -path "$DOCS_ROOT/99-archive/*" -print0)
  else
    echo "[SMOKE] mmdc not found; smoke-render skipped" >&2
  fi
fi

echo "Checked Mermaid sources: $checked_mermaid"
echo "Checked image artifacts: $checked_images"

if [[ "$violations" -gt 0 ]]; then
  echo "Validation failed with $violations violation(s)." >&2
  exit 1
fi

echo "Validation passed."
exit 0
