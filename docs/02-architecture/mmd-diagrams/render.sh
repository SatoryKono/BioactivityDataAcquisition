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

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
THEME_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/theme" && pwd)"
CONFIG="$THEME_DIR/mermaid-config.json"
CSS="$THEME_DIR/custom.css"

# ── Defaults ────────────────────────────────────────────────
SCALE=3          # 3x ≈ 300 DPI
WIDTH=2400
HEIGHT=1800
BG="white"
FORMAT_SVG=1
FORMAT_PNG=1
FILTER="*"
EXTRA_DIRS=()
PUPPETEER_CFG=""
JOBS=4           # parallel jobs

# ── Diagram source directories ──────────────────────────────
DEFAULT_DIRS=(
  "$REPO_ROOT/docs/02-architecture/diagrams"
  "$REPO_ROOT/docs/02-architecture/mmd-diagrams/architecture"
  "$REPO_ROOT/docs/02-architecture/mmd-diagrams/class-diagrams"
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
  --width N           PNG width in pixels     (default: $WIDTH)
  --height N          PNG height in pixels    (default: $HEIGHT)
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

# ── Parse args ──────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --svg-only)     FORMAT_SVG=1; FORMAT_PNG=0;         shift ;;
    --png-only)     FORMAT_SVG=0; FORMAT_PNG=1;         shift ;;
    --scale)        SCALE="$2";                         shift 2 ;;
    --width)        WIDTH="$2";                         shift 2 ;;
    --height)       HEIGHT="$2";                        shift 2 ;;
    --bg)           BG="$2";                            shift 2 ;;
    --filter)       FILTER="$2";                        shift 2 ;;
    --dir)          EXTRA_DIRS+=("$2");                 shift 2 ;;
    --jobs)         JOBS="$2";                          shift 2 ;;
    --puppeteer)    PUPPETEER_CFG="$2";                 shift 2 ;;
    -h|--help)      usage; exit 0 ;;
    *)              log_err "Unknown option: $1"; usage; exit 1 ;;
  esac
done

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

  # Render SVG
  if [[ $FORMAT_SVG -eq 1 ]]; then
    mkdir -p "$svg_dir"
    local svg_out="$svg_dir/${base}.svg"
    if mmdc -i "$src" -o "$svg_out" "${MMDC_ARGS[@]}" -w "$WIDTH" -H "$HEIGHT" -b "$BG" 2>/dev/null; then
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
      # SVG → PNG via rsvg-convert (best quality)
      rsvg-convert -w "$WIDTH" "$svg_dir/${base}.svg" -o "$png_out" 2>/dev/null
    elif [[ $FORMAT_SVG -eq 1 && $HAS_RSVG -eq 2 ]]; then
      # SVG → PNG via inkscape
      inkscape "$svg_dir/${base}.svg" --export-type=png --export-dpi=300 \
        --export-filename="$png_out" 2>/dev/null
    else
      # Direct mmdc → PNG
      mmdc -i "$src" -o "$png_out" "${MMDC_ARGS[@]}" \
        -w "$WIDTH" -H "$HEIGHT" -s "$SCALE" -b "$BG" 2>/dev/null
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
echo ""

if [[ $failed -eq 0 ]]; then
  log_info "All diagrams rendered successfully"
  exit 0
else
  log_warn "$failed diagram(s) failed — check errors above"
  exit 1
fi
