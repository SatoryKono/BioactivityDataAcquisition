#!/bin/bash

# launch-gemini.sh
# Launches Gemini agent with BioETL context in WSL
# Analogous to Codex launch pattern

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
GEMINI_HOME="${PROJECT_ROOT}/.gemini"

# Source environment if available
if [ -f "${GEMINI_HOME}/.env.sh" ]; then
  source "${GEMINI_HOME}/.env.sh"
fi

# Validate configuration
if [ ! -f "${GEMINI_CONFIG}" ]; then
  echo "❌ Gemini config not found: ${GEMINI_CONFIG}"
  echo "   Run: scripts/ai/setup-gemini-wsl.sh"
  exit 1
fi

if [ ! -f "${GEMINI_MCP_SETTINGS}" ]; then
  echo "❌ Gemini MCP settings not found: ${GEMINI_MCP_SETTINGS}"
  exit 1
fi

# Parse arguments
GEMINI_PROFILE="${1:-py-review-orchestrator}"
TASK_MODE="${2:-default}"

echo "🚀 Launching Gemini with profile: ${GEMINI_PROFILE}"
echo "   Config: ${GEMINI_CONFIG}"
echo "   MCP: ${GEMINI_MCP_SETTINGS}"
echo ""

# Determine agent role from profile name
case "${GEMINI_PROFILE}" in
  py-audit-bot|py-debug-bot|py-test-bot)
    AGENT_ROLE="research"
    ;;
  py-config-bot|py-doc-bot)
    AGENT_ROLE="implementation"
    ;;
  *)
    AGENT_ROLE="default"
    ;;
esac

echo "📋 Agent Role: ${AGENT_ROLE}"
echo "   Profile: ${GEMINI_HOME}/agents/${GEMINI_PROFILE}.md"
echo ""

# Load profile if exists
PROFILE_FILE="${GEMINI_HOME}/agents/${GEMINI_PROFILE}.md"
if [ -f "${PROFILE_FILE}" ]; then
  echo "📖 Profile context loaded."
  PROFILE_CONTEXT=$(cat "${PROFILE_FILE}" | head -20)
else
  echo "⚠️  Profile not found: ${PROFILE_FILE}"
  echo "   Using generic Gemini agent."
  PROFILE_CONTEXT="BioETL project - Follow .gemini/agents/GEMINI-RUNTIME.md"
fi

echo ""
echo "=== GEMINI SESSION START ==="
echo ""
echo "Profile: ${GEMINI_PROFILE}"
echo "Role: ${AGENT_ROLE}"
echo "Mode: ${TASK_MODE}"
echo ""
echo "Context:"
echo "${PROFILE_CONTEXT}"
echo ""
echo "To exit: type 'exit' or 'quit'"
echo ""

# Launch Gemini (placeholder — replace with actual Gemini CLI)
# For now, show environment readiness
echo "✓ Gemini environment is ready."
echo "  Run your Gemini commands with:"
echo "    gemini --config='${GEMINI_CONFIG}' --mcp='${GEMINI_MCP_SETTINGS}'"
echo ""
