#!/bin/bash

# setup-gemini-wsl.sh
# Configures Gemini runtime in WSL for BioETL project
# Analogous to Codex setup in .codex/

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
GEMINI_HOME="${PROJECT_ROOT}/.gemini"
MEMORY_DIR="${PROJECT_ROOT}/docs/00-project/ai/memory"

echo "🔧 Setting up Gemini runtime for BioETL (WSL)..."

# Ensure directories exist
mkdir -p "${GEMINI_HOME}/agents"
mkdir -p "${GEMINI_HOME}/skills"
mkdir -p "${MEMORY_DIR}"

# Initialize memory file if not exists
if [ ! -f "${MEMORY_DIR}/gemini-memory.json" ]; then
  echo "📝 Initializing Gemini memory store..."
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
  chmod 644 "${MEMORY_DIR}/gemini-memory.json"
fi

# Verify MCP servers configuration
if [ ! -f "${GEMINI_HOME}/settings.json" ]; then
  echo "❌ MCP settings missing. Please ensure .gemini/settings.json exists."
  exit 1
fi

# Verify runtime config
if [ ! -f "${GEMINI_HOME}/config.toml" ]; then
  echo "❌ Runtime config missing. Please ensure .gemini/config.toml exists."
  exit 1
fi

# Link Codex agent profiles to Gemini (optional: for reference)
echo "🔗 Linking Codex agent profiles for reference..."
CODEX_AGENTS="${PROJECT_ROOT}/.codex/agents"
if [ -d "${CODEX_AGENTS}" ]; then
  ln -sf "${CODEX_AGENTS}/py-audit-bot.md" "${GEMINI_HOME}/agents/" 2>/dev/null || true
  ln -sf "${CODEX_AGENTS}/py-review-orchestrator.md" "${GEMINI_HOME}/agents/" 2>/dev/null || true
  ln -sf "${CODEX_AGENTS}/py-config-bot.md" "${GEMINI_HOME}/agents/" 2>/dev/null || true
fi

# Verify WSL environment variables
if [ -z "$WSLENV" ]; then
  echo "⚠️  WSL environment variables not detected. Setting WSLENV..."
  export WSLENV="GEMINI_HOME:PROJECT_ROOT"
fi

# Test MCP server connectivity (memory server only, non-blocking)
echo "🔌 Verifying MCP configuration..."
if command -v npx &> /dev/null; then
  echo "   ✓ Node.js environment available"
else
  echo "   ⚠️  Node.js not in PATH. Some MCP servers may fail."
fi

if command -v uvx &> /dev/null; then
  echo "   ✓ UV environment available"
else
  echo "   ⚠️  UV not in PATH. Fetch MCP may fail."
fi

# Create shell aliases for quick access
echo ""
echo "📌 Gemini environment ready. Add these to your .bashrc or .zshrc:"
echo ""
echo "  export GEMINI_HOME=\"${GEMINI_HOME}\""
echo "  export GEMINI_CONFIG=\"${GEMINI_HOME}/config.toml\""
echo "  export GEMINI_MCP_SETTINGS=\"${GEMINI_HOME}/settings.json\""
echo ""

# Save environment setup script
GEMINI_ENV_SCRIPT="${GEMINI_HOME}/.env.sh"
cat > "${GEMINI_ENV_SCRIPT}" << 'EOF'
#!/bin/bash
# Source this file to activate Gemini environment in WSL
export GEMINI_HOME="${PROJECT_ROOT}/.gemini"
export GEMINI_CONFIG="${GEMINI_HOME}/config.toml"
export GEMINI_MCP_SETTINGS="${GEMINI_HOME}/settings.json"
export GEMINI_MEMORY_FILE="${PROJECT_ROOT}/docs/00-project/ai/memory/gemini-memory.json"
echo "✓ Gemini environment activated"
EOF
chmod +x "${GEMINI_ENV_SCRIPT}"

echo "✅ Gemini runtime setup complete!"
echo ""
echo "Next steps:"
echo "  1. source ${GEMINI_ENV_SCRIPT}    # Activate environment"
echo "  2. Copy py-* profiles from .codex/agents/ to .gemini/agents/"
echo "  3. Launch Gemini with: gemini --config=${GEMINI_HOME}/config.toml"
echo ""
