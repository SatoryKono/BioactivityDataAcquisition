#!/bin/bash

# lib/tasks/debug.sh - Debug/fix task

# Calculate paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -z "$PROJECT_ROOT" ]; then
  PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"
fi

export PROJECT_ROOT

source "${SCRIPT_DIR}/../utils.sh"

ISSUE="${1}"
AFFECTED_FILE="${2}"
SESSIONS_DIR=$(get_sessions_dir)

mkdir -p "$SESSIONS_DIR"

TASK_FILE="${SESSIONS_DIR}/debug-$(date +%s).md"

print_header
print_section "Debug/Fix Task"

if [ -z "$ISSUE" ]; then
  read -p "Issue/Bug description: " ISSUE
fi

if [ -z "$AFFECTED_FILE" ]; then
  read -p "Affected file/module (optional): " AFFECTED_FILE
fi

AFFECTED_FILE=$(sanitize_path "$AFFECTED_FILE")

echo "Issue: $ISSUE"
[ -n "$AFFECTED_FILE" ] && echo "Affected: $AFFECTED_FILE"

cat > "$TASK_FILE" << EOF
# Debug/Fix Task

**Profile:** py-debug-bot  
**Role:** implementation  
**Created:** $(date)  
**Issue:** $ISSUE  
**Affected:** ${AFFECTED_FILE:-N/A}  

## Problem Statement

$ISSUE

## Constraints
- Follow GEMINI.md standards
- Maintain test coverage ≥85%
- Use structlog for logging (no print)
- Type hints required

## Context
- GEMINI.md (sections 1-4)
- .gemini/agents/py-debug-bot.md
- Affected file: $AFFECTED_FILE

---

## Fix Implementation

[Gemini output will be appended here]

EOF

print_success "Task file created"
print_info "File: $TASK_FILE"
echo ""
print_info "Share this file with Gemini for debugging and fix implementation"
echo ""
