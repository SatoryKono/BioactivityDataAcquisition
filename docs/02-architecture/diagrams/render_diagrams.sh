#!/usr/bin/env bash

# BioETL Diagram Rendering Script
# Renders Mermaid (.mermaid) diagrams to PNG images

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MERMAID_DIR="$SCRIPT_DIR"
IMAGES_DIR="$SCRIPT_DIR/images"

# Defaults (can be overridden via flags)
WIDTH=1200
HEIGHT=800
SCALE=2
BACKGROUND="transparent"
INPUT_GLOB="*.mermaid"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

usage() {
    cat <<'EOF'
Usage: ./render_diagrams.sh [options]

Options:
  --width <px>         Image width in pixels (default: 1200)
  --height <px>        Image height in pixels (default: 800)
  --scale <n>          Render scale factor (default: 2)
  --background <color> Background color (default: transparent)
  --output-dir <path>  Output directory (default: ./images)
  --input-glob <glob>  Input file glob in diagrams dir (default: *.mermaid)
  -h, --help           Show this help
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --width)
            WIDTH="$2"
            shift 2
            ;;
        --height)
            HEIGHT="$2"
            shift 2
            ;;
        --scale)
            SCALE="$2"
            shift 2
            ;;
        --background)
            BACKGROUND="$2"
            shift 2
            ;;
        --output-dir)
            IMAGES_DIR="$2"
            shift 2
            ;;
        --input-glob)
            INPUT_GLOB="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            usage
            exit 1
            ;;
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
    echo "Alternative installation methods:"
    echo "  1. Using yarn: yarn global add @mermaid-js/mermaid-cli"
    echo "  2. Using Docker: see README.md"
    echo ""
    exit 1
fi

echo -e "${GREEN}✓ mermaid-cli (mmdc) found${NC}"
echo ""

# Count total diagrams
shopt -s nullglob
files=("$MERMAID_DIR"/$INPUT_GLOB)
total_diagrams=${#files[@]}

if [ "$total_diagrams" -eq 0 ]; then
    echo -e "${YELLOW}No diagrams found for pattern '$INPUT_GLOB' in $MERMAID_DIR${NC}"
    exit 0
fi

echo "Found $total_diagrams Mermaid diagrams to render"
echo ""

# Render each diagram
count=0
success=0
failed=0

for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        count=$((count + 1))
        filename=$(basename "$file" .mermaid)
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
    fi
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
echo "Creating index file: $INDEX_FILE"

cat > "$INDEX_FILE" << 'EOF'
# BioETL Architecture Diagrams - PNG Index

*Generated: $(date)*

## Rendered Diagrams

EOF

# Add each diagram to index
for file in "$IMAGES_DIR"/*.png; do
    if [ -f "$file" ]; then
        filename=$(basename "$file" .png)
        echo "### $filename" >> "$INDEX_FILE"
        echo "" >> "$INDEX_FILE"
        echo "![${filename}](./${filename}.png)" >> "$INDEX_FILE"
        echo "" >> "$INDEX_FILE"
        echo "---" >> "$INDEX_FILE"
        echo "" >> "$INDEX_FILE"
    fi
done

echo -e "${GREEN}✓${NC} Index file created: $INDEX_FILE"
echo ""

# Summary
if [ $failed -eq 0 ]; then
    echo -e "${GREEN}All diagrams rendered successfully!${NC}"
    exit 0
else
    echo -e "${YELLOW}Some diagrams failed to render. Check errors above.${NC}"
    exit 1
fi
