#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# BioETL — Unified Diagram Renderer
# Renders Mermaid (.mermaid / .mmd) diagrams to SVG + PNG.
#
# Usage:
#   ./render.sh                        # render all docs diagrams (except docs/99-archive/**)
#   ./render.sh --svg-only             # SVG only (fast)
#   ./render.sh --png-only             # PNG only
#   ./render.sh --filter "01-*"        # glob filter on filename
#   ./render.sh --dir docs/02-architecture/diagrams/architecture   # single dir
#   ./render.sh --help
# ─────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if REPO_ROOT_GIT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null)"; then
  REPO_ROOT="$REPO_ROOT_GIT"
else
  REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
fi
THEME_DIR="$(cd "$SCRIPT_DIR/../theme" && pwd)"
CONFIG="$THEME_DIR/mermaid-config.json"
CSS="$THEME_DIR/custom.css"

# ── Defaults ────────────────────────────────────────────────
SCALE=3          # 3x ≈ 300 DPI
LARGE_SCALE=4    # higher PNG scale for large diagrams
LARGE_THRESHOLD=30
PNG_DPI=300
LARGE_PNG_DPI=450
WIDTH=0          # 0 = adaptive (fit to content)
HEIGHT=0         # 0 = adaptive (fit to content)
BG="white"
FORMAT_SVG=1
FORMAT_PNG=1
FILTER="*"
EXTRA_DIRS=()
PUPPETEER_CFG="$THEME_DIR/puppeteer-config.json"
[[ -f "$PUPPETEER_CFG" ]] || PUPPETEER_CFG=""
TEMP_PUPPETEER_CFG=""
JOBS=4           # parallel jobs
FIT=1            # adaptive sizing by default
TEXT_LAYER="fallback-only"   # dual | fo-only | fallback-only
EXCLUDE_PATHS=("docs/99-archive")
MMDC_BIN="${MMDC_BIN:-$REPO_ROOT/scripts/diagrams/mmdc_wrapper.sh}"

# ── Diagram source directories ──────────────────────────────
DEFAULT_DIRS=(
  "$REPO_ROOT/docs"
)

# ── Colours ─────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ── Helpers ─────────────────────────────────────────────────
usage() {
  cat <<EOF
${BOLD}BioETL Diagram Renderer${NC}

Usage: $(basename "$0") [OPTIONS]

Finds all .mermaid / .mmd files in known directories,
renders them to SVG (vector) and PNG (raster, 300 DPI).

Output layout:
  <source-dir>/svg/<name>.svg
  <source-dir>/png/<name>.png

Options:
  --svg-only          Render SVG only (skip PNG conversion)
  --png-only          Render PNG only
  --scale N           PNG scale factor        (default: $SCALE)
  --large-scale N     PNG scale for large diagrams (default: $LARGE_SCALE)
  --large-threshold N @nodes threshold for large-diagram boost (default: $LARGE_THRESHOLD)
  --png-dpi N         PNG DPI for normal diagrams when using SVG converters (default: $PNG_DPI)
  --large-png-dpi N   PNG DPI for large diagrams when using SVG converters (default: $LARGE_PNG_DPI)
  --width N           Viewport width (0=auto) (default: $WIDTH)
  --height N          Viewport height (0=auto)(default: $HEIGHT)
  --no-fit            Use fixed width/height instead of adaptive
  --bg COLOR          Background colour       (default: $BG)
  --filter GLOB       Only render matching    (default: "$FILTER")
  --dir DIR           Add extra source dir    (repeatable)
  --exclude PATH      Exclude path (repeatable, relative to repo root
                      or absolute path; default: docs/99-archive)
  --jobs N            Parallel render jobs    (default: $JOBS)
  --text-layer MODE   Text layer mode: dual | fo-only | fallback-only
                      (default: $TEXT_LAYER)
  --puppeteer FILE    Puppeteer config JSON   (CI sandboxing; defaults to theme/puppeteer-config.json if present)
  -h, --help          Show this help
EOF
  return 0
}

log_info()  { echo -e "${GREEN}[INFO]${NC}  $*"; return 0; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; return 0; }
log_err()   { echo -e "${RED}[ERR]${NC}   $*"; return 0; }
log_step()  { echo -e "${CYAN}[STEP]${NC}  $*"; return 0; }

cleanup_temp_files() {
  [[ -n "$TEMP_PUPPETEER_CFG" ]] && rm -f "$TEMP_PUPPETEER_CFG" || true
  return 0
}
trap cleanup_temp_files EXIT

require_option_value() {
  local option_name="$1"
  local arg_count="$2"
  if [[ "$arg_count" -lt 2 ]]; then
    log_err "Option $option_name requires a value"
    usage
    exit 1
  fi
  return 0
}

resolve_chrome_headless_shell() {
  local env_exec="${PUPPETEER_EXECUTABLE_PATH:-}"
  if [[ -n "$env_exec" ]]; then
    if [[ -x "$env_exec" ]]; then
      echo "$env_exec"
      return 0
    fi
    log_warn "PUPPETEER_EXECUTABLE_PATH is not executable: $env_exec"
  fi

  if command -v chrome-headless-shell >/dev/null 2>&1; then
    command -v chrome-headless-shell
    return 0
  fi

  local cache_root="${HOME:-}/.cache/puppeteer/chrome-headless-shell"
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

  if exec_path="$(resolve_chrome_headless_shell)"; then
    log_info "Using chrome-headless-shell: $exec_path" >&2
  else
    log_warn "chrome-headless-shell not found; Puppeteer will use auto-discovery." >&2
  fi

  if [[ -z "$base_cfg" && -z "$exec_path" ]]; then
    echo ""
    return
  fi

  if [[ -z "$PYTHON_BIN" ]]; then
    log_warn "python not found; using Puppeteer config as-is"
    echo "$base_cfg"
    return
  fi

  out_cfg="$(mktemp "${TMPDIR:-/tmp}/puppeteer-render.XXXXXX.json")"
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
}

configure_browser_library_path() {
  local default_lib_dir="${HOME:-}/.local/share/bioetl/browser-libs/usr/lib/x86_64-linux-gnu"
  local lib_dir="${BIOETL_BROWSER_LIB_DIR:-$default_lib_dir}"

  if [[ -d "$lib_dir" && -f "$lib_dir/libnss3.so" ]]; then
    export LD_LIBRARY_PATH="$lib_dir${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
    log_info "Using browser shared libraries: $lib_dir"
  fi
}

chrome_headless_shell_works() {
  local exec_path="$1"

  bash -c 'exec "$1" "${@:2}"' _ "$exec_path" \
    --headless \
    --no-sandbox \
    --disable-setuid-sandbox \
    --disable-dev-shm-usage \
    --disable-gpu \
    --dump-dom about:blank >/dev/null 2>&1
}

maybe_enable_docker_fallback_for_broken_browser() {
  local exec_path

  [[ "${MMDC_FORCE_DOCKER:-0}" == "1" ]] && return 0

  if ! exec_path="$(resolve_chrome_headless_shell 2>/dev/null)"; then
    return 0
  fi

  if chrome_headless_shell_works "$exec_path"; then
    return 0
  fi

  if command -v docker >/dev/null 2>&1; then
    export MMDC_FORCE_DOCKER=1
    PUPPETEER_CFG=""
    log_warn "chrome-headless-shell failed its smoke test; retrying renders via Docker mmdc fallback."
    return 0
  fi

  log_warn "chrome-headless-shell failed its smoke test and Docker is unavailable; local mmdc may fail."
  return 0
}

# ── Parse args ──────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --svg-only)     FORMAT_SVG=1; FORMAT_PNG=0;         shift ;;
    --png-only)     FORMAT_SVG=0; FORMAT_PNG=1;         shift ;;
    --scale)        require_option_value "$1" "$#"; SCALE="$2";         shift 2 ;;
    --large-scale)  require_option_value "$1" "$#"; LARGE_SCALE="$2";   shift 2 ;;
    --large-threshold) require_option_value "$1" "$#"; LARGE_THRESHOLD="$2"; shift 2 ;;
    --png-dpi)      require_option_value "$1" "$#"; PNG_DPI="$2";       shift 2 ;;
    --large-png-dpi) require_option_value "$1" "$#"; LARGE_PNG_DPI="$2"; shift 2 ;;
    --width)        require_option_value "$1" "$#"; WIDTH="$2";         shift 2 ;;
    --height)       require_option_value "$1" "$#"; HEIGHT="$2";        shift 2 ;;
    --bg)           require_option_value "$1" "$#"; BG="$2";            shift 2 ;;
    --filter)       require_option_value "$1" "$#"; FILTER="$2";        shift 2 ;;
    --dir)          require_option_value "$1" "$#"; EXTRA_DIRS+=("$2"); shift 2 ;;
    --exclude)      require_option_value "$1" "$#"; EXCLUDE_PATHS+=("$2"); shift 2 ;;
    --jobs)         require_option_value "$1" "$#"; JOBS="$2";          shift 2 ;;
    --text-layer)   require_option_value "$1" "$#"; TEXT_LAYER="$2";    shift 2 ;;
    --no-fit)       FIT=0;                                                shift ;;
    --puppeteer)    require_option_value "$1" "$#"; PUPPETEER_CFG="$2"; shift 2 ;;
    -h|--help)      usage; exit 0 ;;
    *)              log_err "Unknown option: $1"; usage; exit 1 ;;
  esac
done

if ! [[ "$SCALE" =~ ^[0-9]+([.][0-9]+)?$ ]]; then
  log_err "--scale must be a positive number (got: $SCALE)"
  exit 1
fi
if ! [[ "$LARGE_SCALE" =~ ^[0-9]+([.][0-9]+)?$ ]]; then
  log_err "--large-scale must be a positive number (got: $LARGE_SCALE)"
  exit 1
fi
if ! [[ "$LARGE_THRESHOLD" =~ ^[0-9]+$ ]]; then
  log_err "--large-threshold must be a non-negative integer (got: $LARGE_THRESHOLD)"
  exit 1
fi
if ! [[ "$PNG_DPI" =~ ^[0-9]+$ ]]; then
  log_err "--png-dpi must be a non-negative integer (got: $PNG_DPI)"
  exit 1
fi
if ! [[ "$LARGE_PNG_DPI" =~ ^[0-9]+$ ]]; then
  log_err "--large-png-dpi must be a non-negative integer (got: $LARGE_PNG_DPI)"
  exit 1
fi
if ! [[ "$WIDTH" =~ ^[0-9]+$ ]]; then
  log_err "--width must be a non-negative integer (got: $WIDTH)"
  exit 1
fi
if ! [[ "$HEIGHT" =~ ^[0-9]+$ ]]; then
  log_err "--height must be a non-negative integer (got: $HEIGHT)"
  exit 1
fi
if ! [[ "$JOBS" =~ ^[0-9]+$ ]] || [[ "$JOBS" -lt 1 ]]; then
  log_err "--jobs must be an integer >= 1 (got: $JOBS)"
  exit 1
fi
if [[ "$TEXT_LAYER" != "dual" && "$TEXT_LAYER" != "fo-only" && "$TEXT_LAYER" != "fallback-only" ]]; then
  log_err "--text-layer must be one of: dual | fo-only | fallback-only (got: $TEXT_LAYER)"
  exit 1
fi

if [[ $FIT -eq 0 ]]; then
  # In fixed mode, treat zero values as "use defaults".
  [[ "$WIDTH" -eq 0 ]] && WIDTH=2400
  [[ "$HEIGHT" -eq 0 ]] && HEIGHT=1800
fi

# ── Determine directories ──────────────────────────────────
if [[ ${#EXTRA_DIRS[@]} -gt 0 ]]; then
  DIRS=("${EXTRA_DIRS[@]}")
else
  DIRS=("${DEFAULT_DIRS[@]}")
fi

# ── Check prerequisites ────────────────────────────────────
echo ""
echo -e "${BOLD}════════════════════════════════════════════${NC}"
echo -e "${BOLD}  BioETL Diagram Renderer${NC}"
echo -e "${BOLD}════════════════════════════════════════════${NC}"
echo ""

if [[ ! -x "$MMDC_BIN" ]]; then
  log_err "mmdc wrapper is not executable: $MMDC_BIN"
  echo ""
  echo "  Provide MMDC_BIN=/path/to/mmdc or restore scripts/diagrams/mmdc_wrapper.sh"
  echo ""
  exit 1
fi
log_info "mmdc $("$MMDC_BIN" --version 2>/dev/null || echo '(version unknown)') found via $MMDC_BIN"

PYTHON_BIN=""
if command -v python3 &>/dev/null; then
  PYTHON_BIN="python3"
elif command -v python &>/dev/null; then
  PYTHON_BIN="python"
fi

NODE_BIN=""
if command -v node &>/dev/null; then
  NODE_BIN="node"
fi

configure_browser_library_path
maybe_enable_docker_fallback_for_broken_browser

HAS_RSVG=0
if command -v rsvg-convert &>/dev/null; then
  HAS_RSVG=1
  log_info "rsvg-convert found (high-quality PNG conversion)"
elif command -v inkscape &>/dev/null; then
  HAS_RSVG=2
  log_info "inkscape found (will use for PNG conversion)"
else
  log_warn "Neither rsvg-convert nor inkscape found; PNG will be rendered from SVG via scripts/diagrams/svg2png.mjs"
fi

if [[ ! -f "$CONFIG" ]]; then
  log_warn "Theme config not found: $CONFIG — using mmdc defaults"
  CONFIG=""
fi

if [[ ! -f "$CSS" ]]; then
  log_warn "Custom CSS not found: $CSS — using mmdc defaults"
  CSS=""
fi

HAS_SVGO=0
if command -v svgo &>/dev/null; then
  HAS_SVGO=1
  log_info "svgo found (SVG optimization enabled)"
else
  log_warn "svgo not found; SVG optimization skipped. Install: npm install -g svgo"
fi

echo ""

if [[ "${MMDC_FORCE_DOCKER:-0}" == "1" ]]; then
  PUPPETEER_CFG=""
  log_info "MMDC_FORCE_DOCKER=1; using the container Puppeteer config"
elif [[ -n "$PUPPETEER_CFG" ]] || [[ -n "${PUPPETEER_EXECUTABLE_PATH:-}" ]] || [[ "$(id -u)" -eq 0 ]]; then
  effective_cfg="$(prepare_puppeteer_cfg "$PUPPETEER_CFG")"
  if [[ -n "$effective_cfg" ]]; then
    PUPPETEER_CFG="$effective_cfg"
    log_info "Using effective Puppeteer config: $PUPPETEER_CFG"
  fi
fi

# ── Collect diagram files ──────────────────────────────────
files=()
exclude_abs=()

for ex in "${EXCLUDE_PATHS[@]}"; do
  if [[ "$ex" = /* ]]; then
    exclude_abs+=("$ex")
  else
    exclude_abs+=("$REPO_ROOT/$ex")
  fi
done

for dir in "${DIRS[@]}"; do
  if [[ "$dir" != /* ]]; then
    dir="$REPO_ROOT/$dir"
  fi
  if [[ ! -d "$dir" ]]; then
    log_warn "Directory not found, skipping: $dir"
    continue
  fi
  while IFS= read -r -d '' f; do
    base_name="$(basename "$f")"
    stem="${base_name%.*}"
    [[ "$base_name" = _* ]] && continue
    [[ "$stem" == $FILTER ]] || continue

    is_excluded=0
    for ex in "${exclude_abs[@]}"; do
      if [[ "$f" == "$ex"/* ]]; then
        is_excluded=1
        break
      fi
    done
    [[ $is_excluded -eq 1 ]] && continue

    files+=("$f")
  done < <(find "$dir" -type f \( -name "*.mermaid" -o -name "*.mmd" \) -print0)
done

if [[ ${#files[@]} -gt 0 ]]; then
  mapfile -t files < <(printf '%s\n' "${files[@]}" | sort -u)
fi

TOTAL=${#files[@]}
if [[ $TOTAL -eq 0 ]]; then
  log_warn "No diagrams found matching filter '$FILTER'"
  exit 0
fi

log_info "Found ${BOLD}$TOTAL${NC} diagrams across ${#DIRS[@]} root directory(ies)"
echo ""

# ── Build mmdc base args ───────────────────────────────────
MMDC_ARGS=()
[[ -n "$CONFIG" ]] && MMDC_ARGS+=(-c "$CONFIG")
[[ -n "$CSS" ]]    && MMDC_ARGS+=("--cssFile" "$CSS")
[[ -n "$PUPPETEER_CFG" ]] && MMDC_ARGS+=(-p "$PUPPETEER_CFG")

# ── Render function ─────────────────────────────────────────
render_one() {
  local src="$1"
  local idx="$2"
  local dir
  dir="$(dirname "$src")"
  local base
  base="$(basename "${src%.*}")"

  local svg_dir="$dir/svg"
  local png_dir="$dir/png"

  # High-res boost for dense diagrams using @nodes metadata.
  local node_count="0"
  local edge_count="0"
  local custom_png_scale=""
  local custom_png_dpi=""
  local is_large=0
  local large_reason=""
  local scale_for_file="$SCALE"
  local dpi_for_file="$PNG_DPI"
  node_count="$(sed -nE "s/^%%[[:space:]]*@nodes[[:space:]]+([0-9]+).*/\1/p" "$src" | head -n 1)"
  if [[ -z "$node_count" ]]; then
    node_count="0"
  fi
  if [[ "$node_count" =~ ^[0-9]+$ ]] && [[ "$node_count" -ge "$LARGE_THRESHOLD" ]]; then
    is_large=1
    large_reason="@nodes=${node_count}"
  fi
  # Fallback heuristic for legacy files without @nodes: dense edge count.
  if [[ "$is_large" -eq 0 ]]; then
    edge_count="$(grep -Ev '^[[:space:]]*%%' "$src" | grep -Ec '(-\.->|==>|-->)' || true)"
    if [[ "$edge_count" =~ ^[0-9]+$ ]] && [[ "$edge_count" -ge "$LARGE_THRESHOLD" ]]; then
      is_large=1
      large_reason="edge-density=${edge_count}"
    fi
  fi
  if [[ "$is_large" -eq 1 ]]; then
    scale_for_file="$LARGE_SCALE"
    dpi_for_file="$LARGE_PNG_DPI"
  fi
  # Per-diagram overrides (optional metadata comments):
  #   %% @png-scale N
  #   %% @png-dpi   N
  custom_png_scale="$(sed -nE "s/^%%[[:space:]]*@png-scale[[:space:]]+([0-9]+).*/\1/p" "$src" | head -n 1)"
  custom_png_dpi="$(sed -nE "s/^%%[[:space:]]*@png-dpi[[:space:]]+([0-9]+).*/\1/p" "$src" | head -n 1)"
  if [[ "$custom_png_scale" =~ ^[0-9]+$ ]] && [[ "$custom_png_scale" -ge 1 ]]; then
    scale_for_file="$custom_png_scale"
  fi
  if [[ "$custom_png_dpi" =~ ^[0-9]+$ ]] && [[ "$custom_png_dpi" -ge 72 ]]; then
    dpi_for_file="$custom_png_dpi"
  fi

  # Build per-format mmdc size args
  local size_args=()
  if [[ $FIT -eq 0 ]]; then
    # Fixed size mode (--no-fit)
    size_args+=(-w "$WIDTH" -H "$HEIGHT")
  fi
  # In adaptive mode (FIT=1), omit -w/-H so mmdc sizes SVG to content

  # Render SVG
  if [[ $FORMAT_SVG -eq 1 ]]; then
    mkdir -p "$svg_dir"
    local svg_out="$svg_dir/${base}.svg"
    if "$MMDC_BIN" -i "$src" -o "$svg_out" "${MMDC_ARGS[@]}" "${size_args[@]}" -b "$BG" 2>/dev/null; then
      # Manage text rendering layers to avoid duplicate labels in viewers
      # that support both foreignObject and fallback text.
      case "$TEXT_LAYER" in
        dual)
          if [[ -n "$PYTHON_BIN" ]]; then
            "$PYTHON_BIN" "$REPO_ROOT/scripts/diagrams/add_svg_text_fallback.py" --fix -f "$svg_out" >/dev/null 2>&1 || true
          fi
          ;;
        fo-only)
          :
          ;;
        fallback-only)
          if [[ -n "$PYTHON_BIN" ]]; then
            if ! "$PYTHON_BIN" "$REPO_ROOT/scripts/diagrams/add_svg_text_fallback.py" --fix -f "$svg_out" >/dev/null 2>&1; then
              log_err "Failed to add SVG fallback text: $svg_out"
              return 1
            fi
            if ! "$PYTHON_BIN" "$REPO_ROOT/scripts/diagrams/strip_svg_foreign_object.py" --fix -f "$svg_out" >/dev/null 2>&1; then
              log_err "Failed to strip foreignObject labels: $svg_out"
              return 1
            fi
          else
            log_err "fallback-only requires python for SVG post-processing"
            return 1
          fi
          ;;
        *)
          log_err "Unsupported TEXT_LAYER mode: $TEXT_LAYER"
          return 1
          ;;
      esac
      # Optimize SVG with svgo if available
      if [[ $HAS_SVGO -eq 1 ]]; then
        svgo --quiet --config "$SCRIPT_DIR/svgo.config.js" "$svg_out" -o "$svg_out" 2>/dev/null || true
      fi
      # Inject CSS overrides for edge label readability
      if [[ -n "$PYTHON_BIN" ]]; then
        "$PYTHON_BIN" "$REPO_ROOT/scripts/diagrams/inject_svg_styles.py" --fix -f "$svg_out" >/dev/null 2>&1 || true
      fi
      echo -e "  ${GREEN}✓${NC} SVG  [$idx/$TOTAL]  $base"
    else
      echo -e "  ${RED}✗${NC} SVG  [$idx/$TOTAL]  $base"
      return 1
    fi
  fi

  # Render PNG
  if [[ $FORMAT_PNG -eq 1 ]]; then
    mkdir -p "$png_dir"
    local png_out="$png_dir/${base}.png"
    local png_svg_source="$svg_dir/${base}.svg"
    local temp_png_svg=""

    # PNG should always be produced from a post-processed SVG so text fallback
    # and foreignObject stripping are preserved in raster output as well.
    if [[ $FORMAT_SVG -eq 0 ]]; then
      temp_png_svg="$(mktemp "${TMPDIR:-/tmp}/bioetl-render-${base}-XXXXXX.svg")"
      if ! "$MMDC_BIN" -i "$src" -o "$temp_png_svg" "${MMDC_ARGS[@]}" "${size_args[@]}" -b "$BG" 2>/dev/null; then
        echo -e "  ${RED}✗${NC} PNG  [$idx/$TOTAL]  $base"
        rm -f "$temp_png_svg"
        return 1
      fi
      case "$TEXT_LAYER" in
        dual)
          if [[ -n "$PYTHON_BIN" ]]; then
            "$PYTHON_BIN" "$REPO_ROOT/scripts/diagrams/add_svg_text_fallback.py" --fix -f "$temp_png_svg" >/dev/null 2>&1 || true
          fi
          ;;
        fo-only)
          :
          ;;
        fallback-only)
          if [[ -n "$PYTHON_BIN" ]]; then
            if ! "$PYTHON_BIN" "$REPO_ROOT/scripts/diagrams/add_svg_text_fallback.py" --fix -f "$temp_png_svg" >/dev/null 2>&1; then
              echo -e "  ${RED}✗${NC} PNG  [$idx/$TOTAL]  $base"
              rm -f "$temp_png_svg"
              return 1
            fi
            if ! "$PYTHON_BIN" "$REPO_ROOT/scripts/diagrams/strip_svg_foreign_object.py" --fix -f "$temp_png_svg" >/dev/null 2>&1; then
              echo -e "  ${RED}✗${NC} PNG  [$idx/$TOTAL]  $base"
              rm -f "$temp_png_svg"
              return 1
            fi
          else
            echo -e "  ${RED}✗${NC} PNG  [$idx/$TOTAL]  $base"
            rm -f "$temp_png_svg"
            return 1
          fi
          ;;
        *)
          echo -e "  ${RED}✗${NC} PNG  [$idx/$TOTAL]  $base"
          rm -f "$temp_png_svg"
          return 1
          ;;
      esac
      if [[ -n "$PYTHON_BIN" ]]; then
        "$PYTHON_BIN" "$REPO_ROOT/scripts/diagrams/inject_svg_styles.py" --fix -f "$temp_png_svg" >/dev/null 2>&1 || true
      fi
      png_svg_source="$temp_png_svg"
    fi

    if [[ $HAS_RSVG -eq 1 ]]; then
      # SVG → PNG via rsvg-convert (adaptive: use SVG intrinsic size)
      if [[ $FIT -eq 0 ]]; then
        rsvg-convert -b "$BG" -w "$WIDTH" -h "$HEIGHT" "$png_svg_source" -o "$png_out" 2>/dev/null
      else
        rsvg-convert -b "$BG" -d "$dpi_for_file" -p "$dpi_for_file" "$png_svg_source" -o "$png_out" 2>/dev/null
      fi
    elif [[ $HAS_RSVG -eq 2 ]]; then
      # SVG → PNG via inkscape
      if [[ $FIT -eq 0 ]]; then
        inkscape "$png_svg_source" --export-type=png --export-width="$WIDTH" \
          --export-height="$HEIGHT" --export-background="$BG" --export-background-opacity=1 \
          --export-filename="$png_out" 2>/dev/null
      else
        inkscape "$png_svg_source" --export-type=png --export-dpi="$dpi_for_file" \
          --export-background="$BG" --export-background-opacity=1 --export-filename="$png_out" 2>/dev/null
      fi
    else
      if [[ -z "$NODE_BIN" ]]; then
        echo -e "  ${RED}✗${NC} PNG  [$idx/$TOTAL]  $base"
        echo "Node.js is required for SVG -> PNG fallback via scripts/diagrams/svg2png.mjs" >&2
        [[ -n "$temp_png_svg" ]] && rm -f "$temp_png_svg"
        return 1
      fi
      if ! PUPPETEER_MODULE_PATH="${PUPPETEER_MODULE_PATH:-/tmp/mermaid-cli-lite/node_modules/puppeteer}" \
        "$NODE_BIN" "$REPO_ROOT/scripts/diagrams/svg2png.mjs" --scale "$scale_for_file" "$png_svg_source" >/dev/null 2>&1; then
        echo -e "  ${RED}✗${NC} PNG  [$idx/$TOTAL]  $base"
        [[ -n "$temp_png_svg" ]] && rm -f "$temp_png_svg"
        return 1
      fi
    fi

    if [[ -n "$temp_png_svg" ]]; then
      rm -f "$temp_png_svg"
    fi

    if [[ -f "$png_out" ]]; then
      local size
      size=$(du -h "$png_out" | cut -f1)
      if [[ "$is_large" -eq 1 ]]; then
        echo -e "  ${GREEN}✓${NC} PNG  [$idx/$TOTAL]  $base  (${size}, hi-res ${large_reason})"
      else
        echo -e "  ${GREEN}✓${NC} PNG  [$idx/$TOTAL]  $base  (${size})"
      fi
    else
      echo -e "  ${RED}✗${NC} PNG  [$idx/$TOTAL]  $base"
      return 1
    fi
  fi

  return 0
}

# ── Main loop ───────────────────────────────────────────────
success=0
failed=0
current_dir=""

if [[ "$JOBS" -eq 1 ]]; then
  for i in "${!files[@]}"; do
    src="${files[$i]}"
    idx=$((i + 1))
    dir="$(dirname "$src")"

    # Print directory header on change
    if [[ "$dir" != "$current_dir" ]]; then
      current_dir="$dir"
      echo ""
      log_step "Directory: ${dir#"$REPO_ROOT/"}"
      echo ""
    fi

    if render_one "$src" "$idx"; then
      success=$((success + 1))
    else
      failed=$((failed + 1))
    fi
  done
else
  log_step "Rendering in parallel with $JOBS jobs..."
  echo ""
  result_dir="$(mktemp -d)"
  active_jobs=0

  for i in "${!files[@]}"; do
    src="${files[$i]}"
    idx=$((i + 1))
    (
      if render_one "$src" "$idx"; then
        printf "ok\n" > "$result_dir/$idx.status"
      else
        printf "fail\n" > "$result_dir/$idx.status"
      fi
    ) &
    active_jobs=$((active_jobs + 1))

    if [[ "$active_jobs" -ge "$JOBS" ]]; then
      wait -n || true
      active_jobs=$((active_jobs - 1))
    fi
  done

  while [[ "$active_jobs" -gt 0 ]]; do
    wait -n || true
    active_jobs=$((active_jobs - 1))
  done

  for i in "${!files[@]}"; do
    idx=$((i + 1))
    if [[ -f "$result_dir/$idx.status" ]] && [[ "$(cat "$result_dir/$idx.status")" == "ok" ]]; then
      success=$((success + 1))
    else
      failed=$((failed + 1))
    fi
  done
  rm -rf "$result_dir"
fi

# ── Generate index files per output directory ───────────────
log_step "Generating index files..."
echo ""

declare -A source_dirs_map=()
for src in "${files[@]}"; do
  src_dir="$(dirname "$src")"
  source_dirs_map["$src_dir"]=1
done
mapfile -t source_dirs < <(printf '%s\n' "${!source_dirs_map[@]}" | sort)

for dir in "${source_dirs[@]}"; do
  for sub in svg png; do
    out_dir="$dir/$sub"
    [[ ! -d "$out_dir" ]] && continue

    index_file="$out_dir/INDEX.md"
    {
      echo "# BioETL Diagrams — ${sub^^} Index"
      echo ""
      echo "_Generated: $(date -Iseconds)_"
      echo ""
      shopt -s nullglob
      for f in "$out_dir"/*."$sub"; do
        name="$(basename "$f" ".$sub")"
        title="${name//-/ }"
        # Capitalize first letter of each word
        title="$(echo "$title" | sed 's/\b[0-9]*\b //;s/\b\(.\)/\u\1/g')"
        echo "## $title"
        echo ""
        if [[ "$sub" == "svg" ]]; then
          echo "![${name}](./${name}.svg)"
        else
          echo "![${name}](./${name}.png)"
        fi
        echo ""
        echo "---"
        echo ""
      done
      shopt -u nullglob
    } > "$index_file"
    echo -e "  ${GREEN}✓${NC} Index: ${index_file#"$REPO_ROOT/"}"
  done
done

# ── Summary ─────────────────────────────────────────────────
echo ""
echo -e "${BOLD}════════════════════════════════════════════${NC}"
echo -e "${BOLD}  Summary${NC}"
echo -e "${BOLD}════════════════════════════════════════════${NC}"
echo ""
echo -e "  Total diagrams:  ${BOLD}$TOTAL${NC}"
echo -e "  ${GREEN}Rendered OK:${NC}     $success"
[[ $failed -gt 0 ]] && echo -e "  ${RED}Failed:${NC}          $failed"
echo ""
echo -e "  Theme:  ${CONFIG:-'(default)'}"
echo -e "  CSS:    ${CSS:-'(none)'}"
echo -e "  Text:   ${TEXT_LAYER}"
echo ""

formats=""
[[ $FORMAT_SVG -eq 1 ]] && formats+="SVG "
[[ $FORMAT_PNG -eq 1 ]] && formats+="PNG "
echo -e "  Formats: ${BOLD}${formats}${NC}"
if [[ $FIT -eq 1 ]]; then
  echo -e "  Layout:  ${BOLD}adaptive${NC} (fit to content, ELK engine)"
else
  echo -e "  Layout:  ${BOLD}fixed${NC} (${WIDTH}x${HEIGHT})"
fi
echo -e "  PNG:     base scale=${SCALE}, large scale=${LARGE_SCALE} (@nodes>=${LARGE_THRESHOLD})"
echo -e "           base dpi=${PNG_DPI}, large dpi=${LARGE_PNG_DPI}"
echo ""

if [[ $failed -eq 0 ]]; then
  log_info "All diagrams rendered successfully"
  exit 0
else
  log_warn "$failed diagram(s) failed — check errors above"
  exit 1
fi
