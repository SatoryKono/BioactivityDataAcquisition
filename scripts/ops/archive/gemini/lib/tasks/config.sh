#!/bin/bash

# lib/tasks/config.sh - Configuration audit task

# Calculate paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -z "$PROJECT_ROOT" ]; then
  PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"
fi

export PROJECT_ROOT

source "${SCRIPT_DIR}/../utils.sh"

SCOPE="${1:-all}"
SESSIONS_DIR=$(get_sessions_dir)

mkdir -p "$SESSIONS_DIR"

TASK_FILE="${SESSIONS_DIR}/config-audit-$(date +%s).md"

print_header
print_section "Configuration Audit Task"

echo "Audit scope: ${SCOPE}"

cat > "$TASK_FILE" << EOF
# Configuration Audit Task

**Profile:** py-config-bot  
**Role:** implementation  
**Created:** $(date)  
**Scope:** ${SCOPE}  

## Task Description

Audit configuration files for BioETL project:
- YAML syntax and structure
- Medallion architecture alignment
- Data loading strategies (null vs full_scan_only)
- Parameter validation

## Scope: $SCOPE

## Context
- GEMINI.md (section 2: Data Flow - Medallion Architecture)
- .gemini/agents/py-config-bot.md

---

## Audit Results

[Gemini output will be appended here]

EOF

print_success "Task file created"
print_info "File: $TASK_FILE"
echo ""
print_info "Share this file with Gemini for configuration audit"
echo ""
