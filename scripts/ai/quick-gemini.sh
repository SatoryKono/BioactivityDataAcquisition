#!/bin/bash

# quick-gemini.sh
# Quick launcher for Gemini - single command shortcuts
# Usage: bash scripts/ai/quick-gemini.sh [command] [args]

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

show_help() {
  cat << 'EOF'
🚀 Quick Gemini Launcher

Usage: bash scripts/ai/quick-gemini.sh [command] [options]

Commands:

  review              Launch code review session
    --staged          Review staged changes (default)
    --file <path>     Review specific file
    --dir <path>      Review directory

  chat [profile]      Interactive chat with agent profile
    Default profile: py-review-orchestrator

  task <type>         Quick task launcher
    - review          Code review
    - config          Configuration audit
    - test            Test generation
    - architecture    Architecture analysis
    - debug           Debug/fix task
    Custom: <profile>

  status              Show Gemini environment status
  setup               Initialize Gemini environment
  sync                Sync profiles from Codex
  interactive         Launch full interactive menu (default)
  help                Show this help message

Examples:

  bash scripts/ai/quick-gemini.sh interactive
  bash scripts/ai/quick-gemini.sh review --staged
  bash scripts/ai/quick-gemini.sh review --file src/bioetl/domain/model.py
  bash scripts/ai/quick-gemini.sh chat py-audit-bot
  bash scripts/ai/quick-gemini.sh task config
  bash scripts/ai/quick-gemini.sh status

EOF
}

show_status() {
  echo -e "${CYAN}📊 Gemini Environment Status${NC}\n"
  
  GEMINI_HOME="${PROJECT_ROOT}/.gemini"
  GEMINI_CONFIG="${GEMINI_HOME}/config.toml"
  GEMINI_MCP_SETTINGS="${GEMINI_HOME}/settings.json"
  GEMINI_MEMORY_FILE="${PROJECT_ROOT}/docs/00-project/ai/memory/gemini-memory.json"
  
  [ -d "$GEMINI_HOME" ] && echo -e "${GREEN}✓${NC} Gemini Home: $GEMINI_HOME" || echo -e "✗ Gemini Home: NOT FOUND"
  [ -f "$GEMINI_CONFIG" ] && echo -e "${GREEN}✓${NC} Config: $(basename $GEMINI_CONFIG)" || echo -e "✗ Config: NOT FOUND"
  [ -f "$GEMINI_MCP_SETTINGS" ] && echo -e "${GREEN}✓${NC} MCP Settings: loaded" || echo -e "✗ MCP Settings: NOT FOUND"
  [ -f "$GEMINI_MEMORY_FILE" ] && echo -e "${GREEN}✓${NC} Memory: $(basename $GEMINI_MEMORY_FILE)" || echo -e "✗ Memory: NOT FOUND"
  
  echo ""
  echo "Profiles:"
  ls -1 "${GEMINI_HOME}"/agents/py-*.md 2>/dev/null | wc -l | xargs echo "  Available:"
  
  echo ""
  echo "Sessions:"
  SESSIONS_DIR="${PROJECT_ROOT}/docs/00-project/ai/sessions"
  [ -d "$SESSIONS_DIR" ] && ls -1 "$SESSIONS_DIR" 2>/dev/null | wc -l | xargs echo "  Total:" || echo "  Total: 0"
}

# Main dispatcher
COMMAND="${1:-interactive}"

case "$COMMAND" in
  interactive)
    bash "${PROJECT_ROOT}/scripts/ai/gemini-interactive.sh"
    ;;
  
  review)
    REVIEW_TYPE="${2:---staged}"
    echo -e "${BLUE}🔍 Code Review Mode${NC}"
    echo "Review Type: $REVIEW_TYPE"
    echo "Profile: py-review-orchestrator"
    # Placeholder for actual review
    ;;
  
  chat)
    PROFILE="${2:-py-review-orchestrator}"
    echo -e "${BLUE}💬 Chat Mode${NC}"
    echo "Profile: $PROFILE"
    # Placeholder for chat
    ;;
  
  task)
    TASK_TYPE="${2:-help}"
    echo -e "${BLUE}📋 Task Mode${NC}"
    echo "Task Type: $TASK_TYPE"
    # Placeholder for tasks
    ;;
  
  status)
    show_status
    ;;
  
  setup)
    bash "${PROJECT_ROOT}/scripts/ai/setup-gemini-wsl.sh"
    ;;
  
  sync)
    bash "${PROJECT_ROOT}/scripts/ai/sync-agents-codex-to-gemini.sh"
    ;;
  
  help|--help|-h)
    show_help
    ;;
  
  *)
    echo "Unknown command: $COMMAND"
    echo ""
    show_help
    exit 1
    ;;
esac
