#!/bin/bash

# BioETL Diagram Rendering Script
# Renders Mermaid (.mermaid/.mmd) diagrams to high-resolution PNG images
# Version: 1.1 | Date: 2026-02-17

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MERMAID_DIR="$SCRIPT_DIR"
IMAGES_DIR="$SCRIPT_DIR/png"

# Configuration
WIDTH=2400
HEIGHT=1800
SCALE=3  # 3x scale ≈ 300 DPI for print
BACKGROUND="transparent"  # or "white" for print

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

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
    echo "Alternative installation methods:"
    echo "  1. Using yarn: yarn global add @mermaid-js/mermaid-cli"
    echo "  2. Using Docker: see README.md"
    echo ""
    exit 1
fi

echo -e "${GREEN}✓ mermaid-cli (mmdc) found${NC}"
echo ""

# Find diagrams (.mermaid + .mmd)
mapfile -d '' diagram_files < <(find "$MERMAID_DIR" -maxdepth 1 -type f \( -name "*.mermaid" -o -name "*.mmd" \) -print0 | sort -z)
total_diagrams=${#diagram_files[@]}

echo "Found $total_diagrams Mermaid diagrams to render (*.mermaid, *.mmd)"
echo ""

# Render each diagram
count=0
success=0
failed=0

for file in "${diagram_files[@]}"; do
    count=$((count + 1))
    base_name=$(basename "$file")
    filename="${base_name%.*}"
    output="$IMAGES_DIR/${filename}.png"

    echo -e "${YELLOW}[$count/$total_diagrams]${NC} Rendering: $filename"

    # Render diagram
    if mmdc -i "$file" \
            -o "$output" \
            -w $WIDTH \
            -H $HEIGHT \
            -s $SCALE \
            -b $BACKGROUND \
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
echo -e "Total diagrams discovered: $total_diagrams"
echo -e "${GREEN}Successfully rendered: $success${NC}"
if [ $failed -gt 0 ]; then
    echo -e "${RED}Failed: $failed${NC}"
fi
echo ""
echo "PNG files are located in: $IMAGES_DIR"
echo ""

# Create index file
INDEX_FILE="$IMAGES_DIR/INDEX.md"
echo "Creating index file: $INDEX_FILE"

{
    echo "# BioETL Architecture Diagrams - PNG Index"
    echo ""
    echo "*Generated: $(date)*"
    echo ""
    echo "## Rendered Diagrams"
    echo ""

    png_count=0
    for file in "$IMAGES_DIR"/*.png; do
        if [ -f "$file" ]; then
            png_count=$((png_count + 1))
            png_name=$(basename "$file" .png)
            echo "### $png_name"
            echo ""
            echo "![${png_name}](./${png_name}.png)"
            echo ""
            echo "---"
            echo ""
        fi
    done

    if [ "$png_count" -eq 0 ]; then
        echo "_No PNG files were generated._"
        echo ""
    fi
} > "$INDEX_FILE"

echo -e "${GREEN}✓${NC} PNG index file created: $INDEX_FILE"
echo ""

# Summary
if [ $failed -eq 0 ]; then
    if [ $total_diagrams -eq 0 ]; then
        echo -e "${YELLOW}No Mermaid source files (*.mermaid, *.mmd) were found in $MERMAID_DIR.${NC}"
    else
        echo -e "${GREEN}All discovered diagrams rendered successfully!${NC}"
    fi
    exit 0
else
    echo -e "${YELLOW}Some diagrams failed to render. Check errors above.${NC}"
    exit 1
fi
