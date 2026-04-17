#!/bin/bash

# lib/reset.sh - Clear memory and reset environment

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Use PROJECT_ROOT from environment, or calculate it
if [ -z "$PROJECT_ROOT" ]; then
  # From lib/ go up 3 levels to project root
  PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
fi

MEMORY_FILE="${PROJECT_ROOT}/docs/00-project/ai/memory/gemini-memory.json"

# Export for sourced utils
export PROJECT_ROOT

source "${SCRIPT_DIR}/utils.sh"

print_header
print_section "Reset Gemini Environment"

echo ""
print_warning "This will clear all memory and reset Gemini"
read -p "Continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
  print_info "Reset cancelled"
  exit 0
fi

if [ -f "$MEMORY_FILE" ]; then
  rm -f "$MEMORY_FILE"
  print_success "Memory cleared"
fi

bash "${SCRIPT_DIR}/setup.sh"

echo ""
print_success "Reset complete!"
echo ""
