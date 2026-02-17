#!/bin/bash

# BioETL Diagram Rendering Script
# Renders Mermaid (.mermaid) diagrams to high-resolution PNG images
# Version: 1.0 | Date: 2026-01-20

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MERMAID_DIR="$SCRIPT_DIR/mermaid"
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

# Count total diagrams
total_diagrams=$(find "$MERMAID_DIR" -name "*.mermaid" | wc -l)
echo "Found $total_diagrams Mermaid diagrams to render"
echo ""

# Render each diagram
count=0
success=0
failed=0

for file in "$MERMAID_DIR"/*.mermaid; do
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
