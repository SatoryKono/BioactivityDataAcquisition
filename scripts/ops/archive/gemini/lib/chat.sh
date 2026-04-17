#!/bin/bash

# lib/chat.sh - Interactive chat with agent profile

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Use PROJECT_ROOT from environment, or calculate it
if [ -z "$PROJECT_ROOT" ]; then
  # From lib/ go up 3 levels to project root
  PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
fi

# Set GEMINI_HOME explicitly (don't rely on get_gemini_home)
GEMINI_HOME="${PROJECT_ROOT}/.gemini"
SESSIONS_DIR="${PROJECT_ROOT}/docs/00-project/ai/sessions"

# Export for use by utils and child scripts
export PROJECT_ROOT GEMINI_HOME SESSIONS_DIR

source "${SCRIPT_DIR}/utils.sh"

PROFILE="${1:-py-review-orchestrator}"

mkdir -p "$SESSIONS_DIR"

print_header
print_section "Chat Mode - $PROFILE"

PROFILE_FILE="${GEMINI_HOME}/agents/${PROFILE}.md"

if [ ! -f "$PROFILE_FILE" ]; then
  print_error "Profile not found: $PROFILE"
  print_info "Available profiles:"
  
  if [ ! -d "${GEMINI_HOME}/agents" ]; then
    print_warning "No agents directory found at: ${GEMINI_HOME}/agents"
    print_info "Run setup first: bash scripts/gemini/gemini setup"
  else
    local count=0
    echo ""
    for p in "${GEMINI_HOME}"/agents/py-*.md; do
      if [ -f "$p" ]; then
        printf "  %2d. %s\n" $((++count)) "$(basename "$p" .md)"
      fi
    done
    if [ $count -eq 0 ]; then
      print_warning "No profiles found. Run sync: bash scripts/gemini/gemini sync"
    fi
    echo ""
  fi
  exit 1
fi

print_success "Profile: $PROFILE"

SESSION_FILE="${SESSIONS_DIR}/chat-$(date +%s).log"
print_info "Session: $(basename $SESSION_FILE)"
print_info "Type 'exit' or 'quit' to end session"
echo ""
echo "----------------------------------------"
echo ""

echo "=== GEMINI CHAT SESSION ===" > "$SESSION_FILE"
echo "Profile: $PROFILE" >> "$SESSION_FILE"
echo "Started: $(date)" >> "$SESSION_FILE"
echo "" >> "$SESSION_FILE"

while true; do
  read -p "You> " user_input
  
  if [ "$user_input" = "exit" ] || [ "$user_input" = "quit" ]; then
    break
  fi
  
  if [ -z "$user_input" ]; then
    continue
  fi
  
  echo "$user_input" >> "$SESSION_FILE"
  
  echo ""
  echo -e "${MAGENTA}Gemini ($PROFILE)>${NC}"
  echo "  [Processing with profile: $PROFILE]"
  echo "  [Context: GEMINI.md + Profile: $PROFILE]"
  echo ""
done

echo "=== SESSION ENDED ===" >> "$SESSION_FILE"
echo "Ended: $(date)" >> "$SESSION_FILE"

echo ""
print_success "Session saved to: $SESSION_FILE"
