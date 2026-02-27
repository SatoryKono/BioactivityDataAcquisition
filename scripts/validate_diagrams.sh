#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
DOCS_ROOT="$REPO_ROOT/docs"
SMOKE_MMDC=0
MMDC_BIN="mmdc"

usage() {
  cat <<'EOF'
Usage: scripts/validate_diagrams.sh [options]

Options:
  --docs <path>       Docs root to scan (default: docs)
  --smoke-mmdc        Run optional Mermaid syntax smoke check via mmdc
  --mmdc-bin <path>   mmdc executable name/path (default: mmdc)
  -h, --help          Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --docs)
      DOCS_ROOT="$2"
      shift 2
      ;;
    --smoke-mmdc)
      SMOKE_MMDC=1
      shift
      ;;
    --mmdc-bin)
      MMDC_BIN="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
done

if [[ "$DOCS_ROOT" != /* ]]; then
  DOCS_ROOT="$REPO_ROOT/$DOCS_ROOT"
fi

if [[ ! -d "$DOCS_ROOT" ]]; then
  echo "Error: docs root does not exist: $DOCS_ROOT" >&2
  exit 2
fi

mapfile -d '' MERMAID_FILES < <(find "$DOCS_ROOT" -type f \( -name '*.mmd' -o -name '*.mermaid' \) -print0 | sort -z)
mapfile -d '' IMAGE_FILES < <(find "$DOCS_ROOT" -type f \( -name '*.png' -o -name '*.svg' \) -print0 | sort -z)

errors=0
checked=0

has_source_meta() {
  local image="$1"
  local dir stem base
  dir="$(dirname "$image")"
  base="$(basename "$image")"
  stem="${base%.*}"

  [[ -f "$dir/$stem.mmd" || -f "$dir/$stem.mermaid" ]] && return 0
  [[ -f "$dir/$base.meta" || -f "$dir/$base.source" || -f "$dir/$base.md" ]] && return 0

  for candidate in "$dir/$stem.meta" "$dir/$stem.source" "$dir/$stem.md"; do
    if [[ -f "$candidate" ]] && grep -Eiq 'source:|parent source:' "$candidate"; then
      return 0
    fi
  done
  return 1
}

for file in "${MERMAID_FILES[@]}"; do
  checked=$((checked + 1))

  base_name="$(basename "$file")"
  if [[ "$base_name" != _* && "$base_name" != 00-legend* ]]; then
    if grep -Eiq '^(graph|flowchart)\b' "$file"; then
      nodes=0
      if grep -Eq '^%%[[:space:]]*@nodes[[:space:]]+[0-9]+' "$file"; then
        nodes=$(grep -E '^%%[[:space:]]*@nodes[[:space:]]+[0-9]+' "$file" | head -n1 | sed -E 's/.*@nodes[[:space:]]+([0-9]+).*/\1/')
      fi
      if [[ "$nodes" -ge 21 ]] && ! grep -Eq '^%%\{init:' "$file"; then
        echo "ERROR [INIT-001] Missing Mermaid init directive for flowchart with @nodes >= 21: $file" >&2
        errors=$((errors + 1))
      fi
    fi
  fi

  if [[ "$file" == *.mermaid ]]; then
    if ! grep -Eq '^%% View:' "$file"; then
      echo "ERROR [META-001] Missing view metadata (%% View:) in: $file" >&2
      errors=$((errors + 1))
    fi
  fi

done

for image in "${IMAGE_FILES[@]}"; do
  checked=$((checked + 1))
  if ! has_source_meta "$image"; then
    echo "ERROR [SOURCE-001] Missing source policy metadata for image: $image" >&2
    errors=$((errors + 1))
  fi
done

if [[ "$SMOKE_MMDC" -eq 1 ]]; then
  if ! command -v "$MMDC_BIN" >/dev/null 2>&1; then
    echo "ERROR [SMOKE-001] mmdc is required for --smoke-mmdc but was not found: $MMDC_BIN" >&2
    errors=$((errors + 1))
  else
    tmp_dir="$(mktemp -d)"
    trap 'rm -rf "$tmp_dir"' EXIT
    idx=0
    for file in "${MERMAID_FILES[@]}"; do
      idx=$((idx + 1))
      out="$tmp_dir/$idx.svg"
      if ! "$MMDC_BIN" -i "$file" -o "$out" >/dev/null 2>&1; then
        echo "ERROR [SMOKE-002] Mermaid syntax/render smoke failed: $file" >&2
        errors=$((errors + 1))
      fi
    done
  fi
fi

if [[ "$errors" -gt 0 ]]; then
  echo "Diagram validation failed: $errors error(s), $checked file(s) checked." >&2
  exit 1
fi

echo "Diagram validation passed: $checked file(s) checked."
