#!/usr/bin/env bash
set -euo pipefail

# shellcheck source=scripts/diagrams/diagram_paths.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/diagram_paths.sh"
DOCS_ROOT="$REPO_ROOT/docs"
CANONICAL_ROOT="$DIAGRAM_ROOT"
SCOPE="all"
THEME_CONFIG="$DIAGRAM_THEME_DIR/mermaid-config.json"
PUPPETEER_CFG="$DIAGRAM_THEME_DIR/puppeteer-config.json"
[[ -f "$PUPPETEER_CFG" ]] || PUPPETEER_CFG=""
TEMP_PUPPETEER_CFG=""
TMP_DIR=""
PYTHON_BIN=""
MMDC_BIN="${MMDC_BIN:-$REPO_ROOT/scripts/diagrams/mmdc_wrapper.sh}"

usage() {
  cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Validate all Mermaid source files in docs/:
  - includes: docs/**/*.mmd, docs/**/*.mermaid
  - excludes: docs/99-archive/**

Options:
  --docs-root DIR     Docs root directory (default: $DOCS_ROOT)
  --scope MODE        Validation scope: all|canonical (default: all)
  --puppeteer FILE    Puppeteer config JSON path
  -h, --help          Show this help
EOF
  return 0
}

cleanup_temp_files() {
  [[ -n "$TEMP_PUPPETEER_CFG" ]] && rm -f "$TEMP_PUPPETEER_CFG" || true
  [[ -n "$TMP_DIR" ]] && rm -rf "$TMP_DIR" || true
  return 0
}
trap cleanup_temp_files EXIT

resolve_chrome_headless_shell() {
  local env_exec="${PUPPETEER_EXECUTABLE_PATH:-}"
  if [[ -n "$env_exec" ]]; then
    if [[ -x "$env_exec" ]]; then
      echo "$env_exec"
      return 0
    fi
    echo "WARN: PUPPETEER_EXECUTABLE_PATH is not executable: $env_exec" >&2
  fi

  if command -v chrome-headless-shell >/dev/null 2>&1; then
    command -v chrome-headless-shell
    return 0
  fi

  local cache_root="${PUPPETEER_CACHE_DIR:-${HOME:-}/.cache/puppeteer}/chrome-headless-shell"
  if [[ -d "$cache_root" ]]; then
    local cached_exec
    cached_exec="$(find "$cache_root" -type f -name chrome-headless-shell 2>/dev/null | sort -V | tail -n 1 || true)"
    if [[ -n "$cached_exec" ]] && [[ -x "$cached_exec" ]]; then
      echo "$cached_exec"
      return 0
    fi
  fi
  return 1
}

prepare_puppeteer_cfg() {
  local base_cfg="$1"
  local exec_path=""
  local out_cfg

  exec_path="$(resolve_chrome_headless_shell || true)"

  if [[ -z "$base_cfg" && -z "$exec_path" ]]; then
    echo ""
    return
  fi

  if [[ -z "$PYTHON_BIN" ]]; then
    echo "$base_cfg"
    return
  fi

  out_cfg="$(mktemp "${TMPDIR:-/tmp}/puppeteer-validate.XXXXXX.json")"
  "$PYTHON_BIN" - <<'PY' "$base_cfg" "$exec_path" "$out_cfg"
import json
import sys
from pathlib import Path

base_cfg, exec_path, out_cfg = sys.argv[1], sys.argv[2], sys.argv[3]
cfg: dict[str, object] = {}

if base_cfg and Path(base_cfg).exists():
    raw = Path(base_cfg).read_text(encoding="utf-8").strip()
    if raw:
        loaded = json.loads(raw)
        if isinstance(loaded, dict):
            cfg = loaded

args_raw = cfg.get("args")
args = [x for x in args_raw if isinstance(x, str)] if isinstance(args_raw, list) else []
required_args = [
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
]
for item in required_args:
    if item not in args:
        args.append(item)
cfg["args"] = args

if exec_path:
    cfg["executablePath"] = exec_path

Path(out_cfg).write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
PY
  TEMP_PUPPETEER_CFG="$out_cfg"
  echo "$out_cfg"
  return 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --docs-root)
      [[ $# -ge 2 ]] || { echo "Missing value for $1" >&2; exit 2; }
      DOCS_ROOT="$2"
      shift 2
      ;;
    --scope)
      [[ $# -ge 2 ]] || { echo "Missing value for $1" >&2; exit 2; }
      SCOPE="$2"
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

case "$SCOPE" in
  all)
    ;;
  canonical)
    DOCS_ROOT="$CANONICAL_ROOT"
    ;;
  *)
    echo "Unsupported scope: $SCOPE (expected: all|canonical)" >&2
    exit 2
    ;;
esac

if [[ ! -x "$MMDC_BIN" ]]; then
  echo "Error: mmdc wrapper is not executable: $MMDC_BIN" >&2
  exit 2
fi

if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
fi

if [[ "$DOCS_ROOT" != /* ]]; then
  DOCS_ROOT="$REPO_ROOT/$DOCS_ROOT"
fi

if [[ ! -d "$DOCS_ROOT" ]]; then
  echo "Error: docs root does not exist for scope '$SCOPE': $DOCS_ROOT" >&2
  exit 2
fi

if [[ -n "$PUPPETEER_CFG" ]] || [[ -n "${PUPPETEER_EXECUTABLE_PATH:-}" ]] || [[ "$(id -u)" -eq 0 ]]; then
  effective_cfg="$(prepare_puppeteer_cfg "$PUPPETEER_CFG")"
  if [[ -n "$effective_cfg" ]]; then
    PUPPETEER_CFG="$effective_cfg"
  fi
fi

TMP_DIR="$(mktemp -d)"

count=0
failed=0
mmdc_args=()
if [[ -f "$THEME_CONFIG" ]]; then
  mmdc_args+=(-c "$THEME_CONFIG")
fi
if [[ -n "$PUPPETEER_CFG" ]]; then
  mmdc_args+=(-p "$PUPPETEER_CFG")
fi

run_validation() {
  local file="$1"
  local out="$2"
  local err="$3"
  if "$MMDC_BIN" -i "$file" -o "$out" "${mmdc_args[@]}" >/dev/null 2>"$err"; then
    return 0
  fi
  "$MMDC_BIN" -i "$file" -o "$out" "${mmdc_args[@]}" >/dev/null 2>"$err"
}

run_validation_with_docker_fallback() {
  local file="$1"
  local out="$2"
  local err="$3"

  if run_validation "$file" "$out" "$err"; then
    return 0
  fi

  if grep -q "Could not find Chrome" "$err" && command -v docker >/dev/null 2>&1; then
    echo "INFO: Chrome runtime unavailable for $file; retrying via Docker mmdc fallback." >&2
    if MMDC_FORCE_DOCKER=1 "$MMDC_BIN" -i "$file" -o "$out" "${mmdc_args[@]}" >/dev/null 2>"$err"; then
      return 0
    fi
  fi

  return 1
}

while IFS= read -r -d '' file; do
  base="$(basename "${file%.*}")"
  [[ "$base" = _* ]] && continue
  count=$((count + 1))
  out="$TMP_DIR/${count}_${base}.svg"
  err="$TMP_DIR/${count}_${base}.err"
  echo "Validating $file"
  if ! run_validation_with_docker_fallback "$file" "$out" "$err"; then
    echo "ERROR: Mermaid validation failed for $file" >&2
    if grep -q "Could not find Chrome" "$err"; then
      echo "HINT: mmdc could not find Chrome/Chromium for Puppeteer." >&2
      echo "      Install browser runtime: npx puppeteer browsers install chrome-headless-shell" >&2
      echo "      Optional: set PUPPETEER_CACHE_DIR=/path/to/cache so Docker fallback can reuse it." >&2
      echo "      Or provide --puppeteer <config.json> with executablePath/args." >&2
      echo "      If Docker is available, the validator automatically retries with MMDC_FORCE_DOCKER=1." >&2
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
