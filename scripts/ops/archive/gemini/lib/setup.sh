#!/bin/bash

# lib/setup.sh - Initialize Gemini environment

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Use PROJECT_ROOT from environment, or calculate it
if [ -z "$PROJECT_ROOT" ]; then
  # From lib/ go up 3 levels to project root
  PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
fi

# Now set all paths based on PROJECT_ROOT
GEMINI_HOME="${PROJECT_ROOT}/.gemini"
MEMORY_DIR="${PROJECT_ROOT}/docs/00-project/ai/memory"
SESSIONS_DIR="${PROJECT_ROOT}/docs/00-project/ai/sessions"

# Export for use by utils
export PROJECT_ROOT GEMINI_HOME MEMORY_DIR SESSIONS_DIR

# Source utilities
source "${SCRIPT_DIR}/utils.sh"

print_header
print_section "Setting up Gemini environment"

# Create directories
mkdir -p "${GEMINI_HOME}/agents"
mkdir -p "${GEMINI_HOME}/skills"
mkdir -p "${MEMORY_DIR}"
mkdir -p "${SESSIONS_DIR}"

print_success "Created directory structure"

# Initialize memory file if not exists
if [ ! -f "${MEMORY_DIR}/gemini-memory.json" ]; then
  cat > "${MEMORY_DIR}/gemini-memory.json" << 'EOF'
{
  "memories": {
    "project_context": {
      "name": "BioETL",
      "architecture": "hexagonal",
      "data_pattern": "medallion",
      "created": "2026-04-14"
    }
  }
}
EOF
  print_success "Initialized memory file"
fi

# Verify config files exist
CONFIG_FILE="${GEMINI_HOME}/config.toml"
MCP_SETTINGS="${GEMINI_HOME}/settings.json"

if [ ! -f "$CONFIG_FILE" ]; then
  print_error "Config missing: $CONFIG_FILE"
  print_info "Make sure .gemini/config.toml exists"
  exit 1
fi

if [ ! -f "$MCP_SETTINGS" ]; then
  print_error "MCP settings missing: $MCP_SETTINGS"
  print_info "Make sure .gemini/settings.json exists"
  exit 1
fi

print_success "Config files verified"

# Check Node.js
if command -v node &> /dev/null; then
  print_success "Node.js available: $(node --version)"
else
  print_warning "Node.js not found (some MCP servers may fail)"
fi

# Check UV
if command -v uvx &> /dev/null; then
  print_success "UV available"
else
  print_warning "UV not found (fetch MCP may fail)"
fi

# Create environment setup script
ENV_SCRIPT="${GEMINI_HOME}/.env.sh"
cat > "$ENV_SCRIPT" << 'ENVEOF'
#!/bin/bash
export GEMINI_HOME="$GEMINI_HOME"
export GEMINI_CONFIG="$GEMINI_HOME/config.toml"
export GEMINI_MCP_SETTINGS="$GEMINI_HOME/settings.json"
export GEMINI_MEMORY_FILE="$PROJECT_ROOT/docs/00-project/ai/memory/gemini-memory.json"
echo "✓ Gemini environment activated"
ENVEOF

chmod +x "$ENV_SCRIPT"

print_success "Environment setup script created"

echo ""
print_success "Gemini runtime setup complete!"
echo ""
print_info "To sync profiles from Codex, run:"
echo "  bash scripts/gemini/gemini sync"
echo ""
