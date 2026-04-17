#!/bin/bash

# lib/status.sh - Show Gemini environment status

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Use PROJECT_ROOT from environment, or calculate it
if [ -z "$PROJECT_ROOT" ]; then
  # From lib/ go up 3 levels to project root
  PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
fi

# Set all paths
GEMINI_HOME="${PROJECT_ROOT}/.gemini"
CONFIG_FILE="${GEMINI_HOME}/config.toml"
MCP_SETTINGS="${GEMINI_HOME}/settings.json"
MEMORY_FILE="${PROJECT_ROOT}/docs/00-project/ai/memory/gemini-memory.json"
SESSIONS_DIR="${PROJECT_ROOT}/docs/00-project/ai/sessions"

# Export for sourced utils
export PROJECT_ROOT

# Source utilities
source "${SCRIPT_DIR}/utils.sh"

print_header
print_section "Gemini Environment Status"

echo ""
echo "Configuration:"
[ -d "$GEMINI_HOME" ] && print_success "Gemini home: $GEMINI_HOME" || print_error "Gemini home: NOT FOUND"
[ -f "$CONFIG_FILE" ] && print_success "Config: $(basename $CONFIG_FILE)" || print_error "Config: NOT FOUND"
[ -f "$MCP_SETTINGS" ] && print_success "MCP settings: loaded" || print_error "MCP settings: NOT FOUND"
[ -f "$MEMORY_FILE" ] && print_success "Memory: $(basename $MEMORY_FILE)" || print_warning "Memory: will be created"

echo ""
echo "Profiles:"
PROFILE_COUNT=$(ls -1 "${GEMINI_HOME}/agents"/py-*.md 2>/dev/null | wc -l)
print_info "Available: $PROFILE_COUNT"

echo ""
echo "Sessions:"
SESSION_COUNT=$(ls -1 "$SESSIONS_DIR" 2>/dev/null | wc -l)
print_info "Total: $SESSION_COUNT"

if [ $SESSION_COUNT -gt 0 ]; then
  echo ""
  echo "Recent sessions:"
  ls -1t "$SESSIONS_DIR" 2>/dev/null | head -5 | sed 's/^/  - /'
fi

echo ""
echo "System:"
if command -v node &> /dev/null; then
  print_success "Node.js: $(node --version)"
else
  print_warning "Node.js: not found"
fi

if command -v uvx &> /dev/null; then
  print_success "UV: available"
else
  print_warning "UV: not found"
fi

echo ""
