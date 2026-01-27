#!/usr/bin/env bash
# cleanup.sh — Quick repository cleanup script for BioETL
#
# Purpose:
# - Remove Python cache directories and compiled files
# - Remove duplicate report files (older hyphen-named versions)
# - Remove temporary files in repository root
#
# Usage:
#   ./scripts/cleanup.sh           # Dry-run (show what would be deleted)
#   ./scripts/cleanup.sh --apply   # Actually delete files
#
# Note: This script is a companion to scripts/repo_cleanup.py
#       For more detailed analysis, use the Python script.

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Parse arguments
APPLY=false
if [[ "${1:-}" == "--apply" ]]; then
    APPLY=true
fi

echo -e "${CYAN}=================================================${NC}"
echo -e "${CYAN}BioETL Repository Cleanup${NC}"
echo -e "${CYAN}=================================================${NC}"
echo "Project root: ${PROJECT_ROOT}"
if [[ "$APPLY" == true ]]; then
    echo -e "Mode: ${RED}APPLY (changes will be made)${NC}"
else
    echo -e "Mode: ${GREEN}DRY-RUN (no changes)${NC}"
fi
echo ""

# Function to count items
count_items() {
    local count
    count=$(echo "$1" | grep -c . 2>/dev/null || echo "0")
    echo "$count"
}

# Function to calculate size
calc_size() {
    local total=0
    while IFS= read -r file; do
        if [[ -n "$file" && -e "$file" ]]; then
            local size
            size=$(du -sb "$file" 2>/dev/null | cut -f1 || echo "0")
            total=$((total + size))
        fi
    done
    # Convert to human readable
    if [[ $total -lt 1024 ]]; then
        echo "${total}B"
    elif [[ $total -lt 1048576 ]]; then
        echo "$((total / 1024))K"
    else
        echo "$((total / 1048576))M"
    fi
}

# ============================================================
# 1. Find Python cache directories and compiled files
# ============================================================
echo -e "${YELLOW}1. Python Cache & Compiled Files${NC}"

# Find __pycache__ directories
PYCACHE_DIRS=$(find "${PROJECT_ROOT}" -type d -name "__pycache__" \
    -not -path "*/.venv/*" \
    -not -path "*/venv/*" \
    -not -path "*/.git/*" \
    -not -path "*/site/*" \
    -not -path "*/data/*" \
    2>/dev/null || true)

# Find .pyc files
PYC_FILES=$(find "${PROJECT_ROOT}" -type f -name "*.pyc" \
    -not -path "*/.venv/*" \
    -not -path "*/venv/*" \
    -not -path "*/.git/*" \
    2>/dev/null || true)

# Count items (handle empty strings properly)
if [[ -n "$PYCACHE_DIRS" ]]; then
    PYCACHE_COUNT=$(echo "$PYCACHE_DIRS" | wc -l)
else
    PYCACHE_COUNT=0
fi

if [[ -n "$PYC_FILES" ]]; then
    PYC_COUNT=$(echo "$PYC_FILES" | wc -l)
else
    PYC_COUNT=0
fi

echo "   __pycache__ directories: $PYCACHE_COUNT"
echo "   .pyc files: $PYC_COUNT"

if [[ -n "$PYCACHE_DIRS" ]]; then
    echo "$PYCACHE_DIRS" | head -5 | while read -r dir; do
        [[ -n "$dir" ]] && echo "     - ${dir#${PROJECT_ROOT}/}"
    done
    [[ $PYCACHE_COUNT -gt 5 ]] && echo "     ... and $((PYCACHE_COUNT - 5)) more"
fi
echo ""

# ============================================================
# 2. Find duplicate report files
# ============================================================
echo -e "${YELLOW}2. Duplicate Report Files${NC}"

REPORTS_DIR="${PROJECT_ROOT}/reports"
DUPLICATE_FILES=""
DUPLICATE_COUNT=0

# Check each known duplicate pair
declare -a OLDER_REPORTS=()
declare -a NEWER_REPORTS=()

check_duplicate() {
    local older="$1"
    local newer="$2"
    local older_path="${REPORTS_DIR}/${older}"
    local newer_path="${REPORTS_DIR}/${newer}"

    if [[ -f "$older_path" && -f "$newer_path" ]]; then
        OLDER_REPORTS+=("$older_path")
        NEWER_REPORTS+=("$newer_path")
        DUPLICATE_COUNT=$((DUPLICATE_COUNT + 1))
        local older_size newer_size
        older_size=$(du -sh "$older_path" 2>/dev/null | cut -f1 || echo "?")
        newer_size=$(du -sh "$newer_path" 2>/dev/null | cut -f1 || echo "?")
        echo "   - ${older} (${older_size}) -> REMOVE"
        echo "     ${newer} (${newer_size}) -> KEEP"
    fi
}

check_duplicate "application-merged.md" "application_merged.md"
check_duplicate "composition-merged.md" "composition_merged.md"
check_duplicate "configs-merged.md" "configs_merged.md"
check_duplicate "documentation-merged.md" "documentation_merged.md"
check_duplicate "domain-merged.md" "domain_merged.md"
check_duplicate "infrastructure-merged.md" "infrastructure_merged.md"
check_duplicate "interfaces-merged.md" "interfaces_merged.md"
check_duplicate "project-structure.md" "project_structure.md"

echo "   Found: ${DUPLICATE_COUNT} duplicate pairs"
echo ""

# ============================================================
# 3. Find temporary root files
# ============================================================
echo -e "${YELLOW}3. Temporary Root Files${NC}"

TEMP_ROOT_FILES=""
TEMP_COUNT=0

# Check for known temp files
for pattern in "test_output.txt" "full_log.txt" "*.log"; do
    for file in "${PROJECT_ROOT}"/${pattern}; do
        if [[ -f "$file" ]]; then
            TEMP_ROOT_FILES="${TEMP_ROOT_FILES}${file}"$'\n'
            TEMP_COUNT=$((TEMP_COUNT + 1))
            size=$(du -sh "$file" 2>/dev/null | cut -f1 || echo "?")
            echo "   - $(basename "$file") (${size})"
        fi
    done
done

echo "   Found: ${TEMP_COUNT} temporary files"
echo ""

# ============================================================
# Summary
# ============================================================
echo -e "${CYAN}=================================================${NC}"
echo -e "${CYAN}Summary${NC}"
echo -e "${CYAN}=================================================${NC}"
echo "   Cache directories: $PYCACHE_COUNT"
echo "   Compiled files: $PYC_COUNT"
echo "   Duplicate reports: $DUPLICATE_COUNT pairs"
echo "   Temp root files: $TEMP_COUNT"
echo ""

# ============================================================
# Apply changes if requested
# ============================================================
if [[ "$APPLY" == true ]]; then
    echo -e "${RED}Applying changes...${NC}"

    # Delete __pycache__ directories
    if [[ -n "$PYCACHE_DIRS" ]]; then
        echo "   Deleting __pycache__ directories..."
        echo "$PYCACHE_DIRS" | while read -r dir; do
            [[ -n "$dir" && -d "$dir" ]] && rm -rf "$dir" && echo "     Deleted: ${dir#${PROJECT_ROOT}/}"
        done
    fi

    # Delete .pyc files
    if [[ -n "$PYC_FILES" ]]; then
        echo "   Deleting .pyc files..."
        echo "$PYC_FILES" | while read -r file; do
            [[ -n "$file" && -f "$file" ]] && rm -f "$file" && echo "     Deleted: ${file#${PROJECT_ROOT}/}"
        done
    fi

    # Delete older duplicate reports
    if [[ ${#OLDER_REPORTS[@]} -gt 0 ]]; then
        echo "   Deleting older duplicate reports..."
        for file in "${OLDER_REPORTS[@]}"; do
            if [[ -f "$file" ]]; then
                rm -f "$file" && echo "     Deleted: ${file#${PROJECT_ROOT}/}"
            fi
        done
    fi

    # Delete temp root files
    if [[ -n "$TEMP_ROOT_FILES" ]]; then
        echo "   Deleting temp root files..."
        echo "$TEMP_ROOT_FILES" | while read -r file; do
            [[ -n "$file" && -f "$file" ]] && rm -f "$file" && echo "     Deleted: ${file#${PROJECT_ROOT}/}"
        done
    fi

    echo -e "${GREEN}Cleanup complete!${NC}"
else
    echo -e "${GREEN}Dry-run complete. No changes made.${NC}"
    echo "Use --apply to actually delete files."
fi
