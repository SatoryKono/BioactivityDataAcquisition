#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# BioETL — Unified Diagram Renderer
# Renders Mermaid (.mermaid / .mmd) diagrams to SVG + PNG.
#
# Usage:
#   ./render.sh                        # render all diagrams
#   ./render.sh --svg-only             # SVG only (fast)
#   ./render.sh --png-only             # PNG only
#   ./render.sh --filter "01-*"        # glob filter on filename
#   ./render.sh --dir docs/02-architecture/mmd-diagrams/architecture   # single dir
#   ./render.sh --help
# ─────────────────────────────────────────────────────────────
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
THEME_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/theme" && pwd)"
CONFIG="$THEME_DIR/mermaid-config.json"
CSS="$THEME_DIR/custom.css"

# ── Defaults ────────────────────────────────────────────────
SCALE=3          # 3x ≈ 300 DPI
WIDTH=0          # 0 = adaptive (fit to content)
HEIGHT=0         # 0 = adaptive (fit to content)
BG="white"
FORMAT_SVG=1
FORMAT_PNG=1
FILTER="*"
EXTRA_DIRS=()
PUPPETEER_CFG=""
JOBS=4           # parallel jobs
FIT=1            # adaptive sizing by default

# ── Diagram source directories ──────────────────────────────
DEFAULT_DIRS=(
  "$REPO_ROOT/docs/02-architecture/mmd-diagrams/architecture"
  "$REPO_ROOT/docs/02-architecture/mmd-diagrams/class-diagrams"
  "$REPO_ROOT/docs/02-architecture/mmd-diagrams/foundation"
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
  --width N           Viewport width (0=auto) (default: $WIDTH)
  --height N          Viewport height (0=auto)(default: $HEIGHT)
  --no-fit            Use fixed width/height instead of adaptive
  --bg COLOR          Background colour       (default: $BG)
  --filter GLOB       Only render matching    (default: "$FILTER")
  --dir DIR           Add extra source dir    (repeatable)
  --jobs N            Parallel render jobs    (default: $JOBS)
  --puppeteer FILE    Puppeteer config JSON   (CI sandboxing)
  -h, --help          Show this help
EOF
}

log_info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_err()   { echo -e "${RED}[ERR]${NC}   $*"; }
log_step()  { echo -e "${CYAN}[STEP]${NC}  $*"; }

require_option_value() {
  local option_name="$1"
  local arg_count="$2"
  if [[ "$arg_count" -lt 2 ]]; then
    log_err "Option $option_name requires a value"
    usage
    exit 1
  fi
}

# ── Parse args ──────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --svg-only)     FORMAT_SVG=1; FORMAT_PNG=0;         shift ;;
    --png-only)     FORMAT_SVG=0; FORMAT_PNG=1;         shift ;;
    --scale)        require_option_value "$1" "$#"; SCALE="$2";         shift 2 ;;
    --width)        require_option_value "$1" "$#"; WIDTH="$2";         shift 2 ;;
    --height)       require_option_value "$1" "$#"; HEIGHT="$2";        shift 2 ;;
    --bg)           require_option_value "$1" "$#"; BG="$2";            shift 2 ;;
    --filter)       require_option_value "$1" "$#"; FILTER="$2";        shift 2 ;;
    --dir)          require_option_value "$1" "$#"; EXTRA_DIRS+=("$2"); shift 2 ;;
    --jobs)         require_option_value "$1" "$#"; JOBS="$2";          shift 2 ;;
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

if ! command -v mmdc &>/dev/null; then
  log_err "mermaid-cli (mmdc) not installed"
  echo ""
  echo "  Install:  npm install -g @mermaid-js/mermaid-cli"
  echo "  Or:       npx @mermaid-js/mermaid-cli --help"
  echo ""
  exit 1
fi
log_info "mmdc $(mmdc --version 2>/dev/null || echo '(version unknown)') found"

HAS_RSVG=0
if command -v rsvg-convert &>/dev/null; then
  HAS_RSVG=1
  log_info "rsvg-convert found (high-quality PNG conversion)"
elif command -v inkscape &>/dev/null; then
  HAS_RSVG=2
  log_info "inkscape found (will use for PNG conversion)"
else
  log_warn "Neither rsvg-convert nor inkscape found; mmdc will render PNG directly"
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

# ── Collect diagram files ──────────────────────────────────
files=()
for dir in "${DIRS[@]}"; do
  if [[ ! -d "$dir" ]]; then
    log_warn "Directory not found, skipping: $dir"
    continue
  fi
  shopt -s nullglob
  for f in "$dir"/$FILTER.mermaid "$dir"/$FILTER.mmd; do
    [[ -f "$f" ]] && files+=("$f")
  done
  shopt -u nullglob
done

TOTAL=${#files[@]}
if [[ $TOTAL -eq 0 ]]; then
  log_warn "No diagrams found matching filter '$FILTER'"
  exit 0
fi

log_info "Found ${BOLD}$TOTAL${NC} diagrams across ${#DIRS[@]} directories"
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
    if mmdc -i "$src" -o "$svg_out" "${MMDC_ARGS[@]}" "${size_args[@]}" -b "$BG" 2>/dev/null; then
      # Optimize SVG with svgo if available
      if [[ $HAS_SVGO -eq 1 ]]; then
        svgo --quiet --config "$THEME_DIR/../svgo.config.js" "$svg_out" -o "$svg_out" 2>/dev/null || true
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

    if [[ $FORMAT_SVG -eq 1 && $HAS_RSVG -eq 1 ]]; then
      # SVG → PNG via rsvg-convert (adaptive: use SVG intrinsic size)
      if [[ $FIT -eq 0 ]]; then
        rsvg-convert -w "$WIDTH" -h "$HEIGHT" "$svg_dir/${base}.svg" -o "$png_out" 2>/dev/null
      else
        rsvg-convert -d 300 -p 300 "$svg_dir/${base}.svg" -o "$png_out" 2>/dev/null
      fi
    elif [[ $FORMAT_SVG -eq 1 && $HAS_RSVG -eq 2 ]]; then
      # SVG → PNG via inkscape
      if [[ $FIT -eq 0 ]]; then
        inkscape "$svg_dir/${base}.svg" --export-type=png --export-width="$WIDTH" \
          --export-height="$HEIGHT" --export-filename="$png_out" 2>/dev/null
      else
        inkscape "$svg_dir/${base}.svg" --export-type=png --export-dpi=300 \
          --export-filename="$png_out" 2>/dev/null
      fi
    else
      # Direct mmdc → PNG (adaptive: use -s scale only)
      mmdc -i "$src" -o "$png_out" "${MMDC_ARGS[@]}" \
        "${size_args[@]}" -s "$SCALE" -b "$BG" 2>/dev/null
    fi

    if [[ -f "$png_out" ]]; then
      local size
      size=$(du -h "$png_out" | cut -f1)
      echo -e "  ${GREEN}✓${NC} PNG  [$idx/$TOTAL]  $base  (${size})"
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

for dir in "${DIRS[@]}"; do
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
echo ""

if [[ $failed -eq 0 ]]; then
  log_info "All diagrams rendered successfully"
  exit 0
else
  log_warn "$failed diagram(s) failed — check errors above"
  exit 1
fi
