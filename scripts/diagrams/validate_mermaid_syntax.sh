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
INCLUDE_SOURCES=1
INCLUDE_EMBEDDED=0

usage() {
  cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Validate all Mermaid source files in docs/:
  - includes: docs/**/*.mmd, docs/**/*.mermaid
  - optionally includes fenced Mermaid diagrams in active Markdown docs
  - excludes: docs/99-archive/**

Options:
  --docs-root DIR     Docs root directory (default: $DOCS_ROOT)
  --scope MODE        Validation scope: all|canonical (default: all)
  --include-embedded  Also validate fenced Mermaid blocks with diagram declarations
  --embedded-only     Validate fenced Mermaid blocks only
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

chrome_headless_shell_is_runnable() {
  local candidate="$1"
  [[ -n "$candidate" && -x "$candidate" ]] || return 1
  # Prefer dependency resolution check: broken puppeteer caches often have the
  # binary present but missing shared libraries (libnss3, etc.).
  if command -v ldd >/dev/null 2>&1; then
    if ldd "$candidate" 2>/dev/null | grep -Eq 'not found'; then
      return 1
    fi
    return 0
  fi
  "$candidate" --version >/dev/null 2>&1
}

resolve_chrome_headless_shell() {
  local env_exec="${PUPPETEER_EXECUTABLE_PATH:-}"
  if [[ -n "$env_exec" ]]; then
    if chrome_headless_shell_is_runnable "$env_exec"; then
      echo "$env_exec"
      return 0
    fi
    echo "WARN: PUPPETEER_EXECUTABLE_PATH is not runnable: $env_exec" >&2
  fi

  if command -v chrome-headless-shell >/dev/null 2>&1; then
    local system_exec
    system_exec="$(command -v chrome-headless-shell)"
    if chrome_headless_shell_is_runnable "$system_exec"; then
      echo "$system_exec"
      return 0
    fi
  fi

  local cache_root="${PUPPETEER_CACHE_DIR:-${HOME:-}/.cache/puppeteer}/chrome-headless-shell"
  if [[ -d "$cache_root" ]]; then
    local cached_exec
    cached_exec="$(find "$cache_root" -type f -name chrome-headless-shell 2>/dev/null | sort -V | tail -n 1 || true)"
    if chrome_headless_shell_is_runnable "$cached_exec"; then
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
    --include-embedded)
      INCLUDE_EMBEDDED=1
      shift
      ;;
    --embedded-only)
      INCLUDE_SOURCES=0
      INCLUDE_EMBEDDED=1
      shift
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

# Only inject a Puppeteer config when a runnable Chrome is available or CI
# explicitly provided one. Passing -p without a browser forces mermaid-cli to
# look at an empty host/container cache and fail with "Could not find Chromium",
# including Docker fallback runs that otherwise ship a working browser image.
runnable_chrome=""
runnable_chrome="$(resolve_chrome_headless_shell || true)"
if [[ -n "$runnable_chrome" ]] || [[ -n "${PUPPETEER_EXECUTABLE_PATH:-}" ]] || [[ "$(id -u)" -eq 0 ]]; then
  if [[ -n "$PUPPETEER_CFG" ]] || [[ -n "${PUPPETEER_EXECUTABLE_PATH:-}" ]] || [[ "$(id -u)" -eq 0 ]]; then
    effective_cfg="$(prepare_puppeteer_cfg "$PUPPETEER_CFG")"
    if [[ -n "$effective_cfg" ]]; then
      PUPPETEER_CFG="$effective_cfg"
    fi
  fi
elif [[ -n "$PUPPETEER_CFG" ]]; then
  # Keep optional args-only configs when the file exists and does not hardcode
  # a missing executablePath.
  if [[ -f "$PUPPETEER_CFG" ]] && ! grep -Eq '"executablePath"' "$PUPPETEER_CFG"; then
    :
  else
    PUPPETEER_CFG=""
  fi
fi

TMP_DIR="$(mktemp -d)"

count=0
failed=0
mmdc_args=()
if [[ -f "$THEME_CONFIG" ]]; then
  mmdc_args+=(-c "$THEME_CONFIG")
fi
# Only pass -p when a runnable browser was resolved (CI host install) so we can
# apply --no-sandbox args. Without a runnable browser, let Docker image
# chromium use its defaults; an empty -p config can force a missing cache path.
if [[ -n "$PUPPETEER_CFG" && -n "$runnable_chrome" ]]; then
  mmdc_args+=(-p "$PUPPETEER_CFG")
fi

# Extract the Mermaid source from either a pure diagram file or a composite
# .mmd document. Some historical .mmd files contain repository metadata before
# the diagram and explanatory Markdown after a closing fence; mmdc must receive
# the diagram section only, while malformed/undetectable sources still fail.
prepare_mermaid_input() {
  local file="$1"
  local prepared="$2"
  awk '
    function is_diagram_start(line) {
      return line ~ /^[[:space:]]*(architecture-beta|block-beta|C4[A-Za-z]*|classDiagram(-v2)?|erDiagram|flowchart|gantt|gitGraph|graph|journey|kanban|mindmap|packet-beta|pie|quadrantChart|radar-beta|requirementDiagram|sankey-beta|sequenceDiagram|stateDiagram(-v2)?|timeline|treemap|xychart-beta|zenuml)([[:space:]]|$)/
    }

    BEGIN {
      diagram_started=0
      preamble_count=0
    }

    diagram_started == 0 {
      if (is_diagram_start($0)) {
        for (idx=1; idx<=preamble_count; idx++) {
          print preamble[idx]
        }
        print
        diagram_started=1
        next
      }

      if ($0 ~ /^[[:space:]]*$/ || $0 ~ /^[[:space:]]*%%/) {
        preamble[++preamble_count]=$0
      } else {
        delete preamble
        preamble_count=0
      }
      next
    }

    /^[[:space:]]*```[[:space:]]*$/ { exit }
    { print }
  ' "$file" >"$prepared"
}

run_validation() {
  local file="$1"
  local out="$2"
  local err="$3"
  local prepared="$TMP_DIR/prepared_$(basename "$file").mmd"
  prepare_mermaid_input "$file" "$prepared"
  if "$MMDC_BIN" -i "$prepared" -o "$out" "${mmdc_args[@]}" >/dev/null 2>"$err"; then
    return 0
  fi
  "$MMDC_BIN" -i "$prepared" -o "$out" "${mmdc_args[@]}" >/dev/null 2>"$err"
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

validate_file() {
  local file="$1"
  local label="$2"
  local base
  local out
  local err

  base="$(basename "${file%.*}")"
  [[ "$base" = _* ]] && return 0
  count=$((count + 1))
  out="$TMP_DIR/${count}_${base}.svg"
  err="$TMP_DIR/${count}_${base}.err"
  echo "Validating $label"
  if ! run_validation_with_docker_fallback "$file" "$out" "$err"; then
    echo "ERROR: Mermaid validation failed for $label" >&2
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
}

if [[ "$INCLUDE_SOURCES" -eq 1 ]]; then
  while IFS= read -r -d '' file; do
    validate_file "$file" "$file"
  done < <(find "$DOCS_ROOT" -type f \( -name "*.mermaid" -o -name "*.mmd" \) \
    -not -path "$DOCS_ROOT/99-archive/*" -print0)
fi

if [[ "$INCLUDE_EMBEDDED" -eq 1 ]]; then
  if [[ -z "$PYTHON_BIN" ]]; then
    echo "Error: python is required for embedded Mermaid extraction" >&2
    exit 2
  fi

  embedded_dir="$TMP_DIR/embedded-mermaid"
  embedded_manifest="$TMP_DIR/embedded-mermaid.tsv"
  mkdir -p "$embedded_dir"
  "$PYTHON_BIN" - <<'PY' "$DOCS_ROOT" "$embedded_dir" "$embedded_manifest"
from __future__ import annotations

import hashlib
import os
import re
import sys
from pathlib import Path

docs_root = Path(sys.argv[1])
out_dir = Path(sys.argv[2])
manifest = Path(sys.argv[3])

fence_re = re.compile(r"^```\s*mermaid\s*$", re.IGNORECASE)
decl_re = re.compile(
    r"^\s*(flowchart|graph|stateDiagram|classDiagram|sequenceDiagram|erDiagram|mindmap|gantt|pie|xychart|C4Context|C4Container|C4Component|C4Dynamic)\b",
    re.IGNORECASE,
)

rows: list[str] = []
skipped_dirs = {"99-archive", "reports", "site"}
for dirpath, dirnames, filenames in os.walk(docs_root):
    dirnames[:] = [item for item in dirnames if item not in skipped_dirs]
    for filename in sorted(filenames):
        if not filename.endswith(".md"):
            continue
        md_path = Path(dirpath) / filename
        try:
            lines = md_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue

        in_block = False
        block: list[str] = []
        start_line = 0
        for line_no, line in enumerate(lines, start=1):
            if not in_block:
                if fence_re.match(line.strip()):
                    in_block = True
                    block = []
                    start_line = line_no
                continue

            if line.strip().startswith("```"):
                block_text = "\n".join(block).strip()
                if block_text and any(decl_re.match(item) for item in block):
                    digest = hashlib.sha1(
                        f"{md_path.as_posix()}:{start_line}".encode("utf-8")
                    ).hexdigest()[:12]
                    out_path = out_dir / f"embedded-{len(rows) + 1:04d}-{digest}.mmd"
                    out_path.write_text(block_text + "\n", encoding="utf-8")
                    rows.append(f"{out_path.as_posix()}\t{md_path.as_posix()}:{start_line}")
                in_block = False
                block = []
                continue

            block.append(line)

manifest.write_text("\n".join(rows) + ("\n" if rows else ""), encoding="utf-8")
print(f"Extracted {len(rows)} embedded Mermaid diagram block(s) for syntax validation.")
PY

  while IFS=$'\t' read -r file label; do
    [[ -z "$file" ]] && continue
    validate_file "$file" "$label"
  done < "$embedded_manifest"
fi

if [[ "$failed" -gt 0 ]]; then
  echo "Validation failed: $failed of $count diagram(s) failed." >&2
  exit 1
fi

echo "Validation passed: $count diagram(s) checked."
