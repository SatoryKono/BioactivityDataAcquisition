#!/usr/bin/env bash

# BioETL Diagram Rendering Script
# Renders Mermaid (.mermaid/.mmd) diagrams to high-resolution PNG images
# Version: 2.0 | Date: 2026-02-17
#
# Consolidated from branches:
#   - establish-diagram-structure (mermaid/ → png/ layout)
#   - update-python-script-instructions (CLI flags, env bash, pipefail)
#   - update-render_diagrams.sh (dual .mermaid/.mmd support)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MERMAID_DIR="$SCRIPT_DIR/mermaid"
IMAGES_DIR="$SCRIPT_DIR/png"

# Defaults
WIDTH=2400
HEIGHT=1800
SCALE=3  # 3x scale ≈ 300 DPI for print
BACKGROUND="transparent"  # or "white" for print
INPUT_GLOB="*.mermaid *.mmd"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

usage() {
    cat <<USAGE
Usage: $(basename "$0") [OPTIONS]

Render Mermaid diagrams from mermaid/ to png/.

Options:
  --width N         Image width in pixels      (default: $WIDTH)
  --height N        Image height in pixels     (default: $HEIGHT)
  --scale N         Scale factor               (default: $SCALE)
  --background STR  Background color           (default: $BACKGROUND)
  --output-dir DIR  Output directory           (default: $IMAGES_DIR)
  --input-glob PAT  File glob pattern(s)       (default: "$INPUT_GLOB")
  -h, --help        Show this help message
USAGE
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --width)       WIDTH="$2";       shift 2 ;;
        --height)      HEIGHT="$2";      shift 2 ;;
        --scale)       SCALE="$2";       shift 2 ;;
        --background)  BACKGROUND="$2";  shift 2 ;;
        --output-dir)  IMAGES_DIR="$2";  shift 2 ;;
        --input-glob)  INPUT_GLOB="$2";  shift 2 ;;
        -h|--help)     usage; exit 0 ;;
        *)             echo "Unknown option: $1"; usage; exit 1 ;;
    esac
done

echo "========================================="
echo "BioETL Diagram Rendering"
echo "========================================="
echo ""

# Create images directory
mkdir -p "$IMAGES_DIR"

# Check for mmdc (mermaid-cli)
if ! command -v mmdc &> /dev/null; then
    echo -e "${RED}Error: mermaid-cli (mmdc) is not installed${NC}"
    echo ""
    echo "To install mermaid-cli:"
    echo "  npm install -g @mermaid-js/mermaid-cli"
    echo ""
    exit 1
fi

echo -e "${GREEN}✓ mermaid-cli (mmdc) found${NC}"
echo ""

# Collect diagram files (both .mermaid and .mmd)
shopt -s nullglob
files=()
for pattern in $INPUT_GLOB; do
    files+=("$MERMAID_DIR"/$pattern)
done
shopt -u nullglob

total_diagrams=${#files[@]}

if [[ $total_diagrams -eq 0 ]]; then
    echo -e "${YELLOW}No diagrams found in $MERMAID_DIR matching: $INPUT_GLOB${NC}"
    exit 0
fi

echo "Found $total_diagrams Mermaid diagrams to render"
echo "  Source: $MERMAID_DIR"
echo "  Output: $IMAGES_DIR"
echo "  Dimensions: ${WIDTH}x${HEIGHT} @ ${SCALE}x scale"
echo ""

# Render each diagram
count=0
success=0
failed=0

for file in "${files[@]}"; do
    count=$((count + 1))
    # Strip any extension (.mermaid or .mmd)
    filename=$(basename "${file%.*}")
    output="$IMAGES_DIR/${filename}.png"

    echo -e "${YELLOW}[$count/$total_diagrams]${NC} Rendering: $filename"

    # Render diagram
    if mmdc -i "$file" \
            -o "$output" \
            -w "$WIDTH" \
            -H "$HEIGHT" \
            -s "$SCALE" \
            -b "$BACKGROUND" \
            2>/dev/null; then

        # Check if file was created
        if [ -f "$output" ]; then
            size=$(du -h "$output" | cut -f1)
            dimensions=$(identify -format "%wx%h" "$output" 2>/dev/null || echo "unknown")
            echo -e "  ${GREEN}✓${NC} Created: $output"
            echo -e "    Size: $size | Dimensions: $dimensions"
            success=$((success + 1))
        else
            echo -e "  ${RED}✗${NC} Error: Output file not created"
            failed=$((failed + 1))
        fi
    else
        echo -e "  ${RED}✗${NC} Error rendering diagram"
        failed=$((failed + 1))
    fi

    echo ""
done

echo "========================================="
echo "Rendering Complete"
echo "========================================="
echo -e "Total diagrams: $total_diagrams"
echo -e "${GREEN}Successfully rendered: $success${NC}"
if [ $failed -gt 0 ]; then
    echo -e "${RED}Failed: $failed${NC}"
fi
echo ""
echo "PNG files are located in: $IMAGES_DIR"
echo ""

# Create index file
INDEX_FILE="$IMAGES_DIR/INDEX.md"
{
    echo "# BioETL Architecture Diagrams - PNG Index"
    echo ""
    echo "*Generated: $(date)*"
    echo ""
    echo "## Rendered Diagrams"
    echo ""
    for file in "$IMAGES_DIR"/*.png; do
        if [ -f "$file" ]; then
            filename=$(basename "$file" .png)
            echo "### $filename"
            echo ""
            echo "![${filename}](./${filename}.png)"
            echo ""
            echo "---"
            echo ""
        fi
    done
} > "$INDEX_FILE"

if [[ $total_diagrams -gt 0 && -f "$INDEX_FILE" ]]; then
    echo -e "${GREEN}✓${NC} Index file created: $INDEX_FILE"
else
    echo -e "${YELLOW}No PNGs to index.${NC}"
fi
echo ""

# Summary
if [ $failed -eq 0 ]; then
    echo -e "${GREEN}All diagrams rendered successfully!${NC}"
    exit 0
else
    echo -e "${YELLOW}Some diagrams failed to render. Check errors above.${NC}"
    exit 1
fi
