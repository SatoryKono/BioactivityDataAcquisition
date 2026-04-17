#!/bin/bash

# lib/tasks/architecture.sh - Architecture analysis task

# Calculate paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -z "$PROJECT_ROOT" ]; then
  PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"
fi

export PROJECT_ROOT

source "${SCRIPT_DIR}/../utils.sh"

FOCUS="${1:-debt}"
SESSIONS_DIR=$(get_sessions_dir)

mkdir -p "$SESSIONS_DIR"

TASK_FILE="${SESSIONS_DIR}/arch-analysis-$(date +%s).md"

print_header
print_section "Architecture Analysis Task"

FOCUS_NAME=""
case "$FOCUS" in
  debt) FOCUS_NAME="Technical Debt" ;;
  dependencies) FOCUS_NAME="Dependency Violations" ;;
  layers) FOCUS_NAME="Layer Isolation" ;;
  ports) FOCUS_NAME="Port Coverage" ;;
  *) print_error "Unknown focus: $FOCUS"; exit 1 ;;
esac

echo "Analysis focus: $FOCUS_NAME"

cat > "$TASK_FILE" << EOF
# Architecture Analysis Task

**Profile:** py-architecture-debt-bot  
**Role:** default (orchestration)  
**Created:** $(date)  
**Focus:** $FOCUS_NAME  

## Task Description

Analyze BioETL architecture against hexagonal/ports-adapters pattern:
- Layer isolation: domain → application → infrastructure
- Port contracts: all external deps abstracted via Protocols
- Dependency injection: no concrete instantiation in domain/app
- Domain purity: no I/O in domain layer

## Focus: $FOCUS_NAME

## Constraints (from GEMINI.md)
- Domain MUST NOT import infrastructure
- ALL I/O via Ports (e.g., LoggerPort, StoragePort, HTTPPort)
- Dependency injection via __init__ only
- Assembly logic in src/bioetl/composition/

## Context
- GEMINI.md (section 1: Core Architecture)
- .gemini/agents/py-architecture-debt-bot.md
- src/bioetl/domain/ports/ (existing contracts)

---

## Analysis Results

[Gemini output will be appended here]

EOF

print_success "Task file created"
print_info "File: $TASK_FILE"
echo ""
print_info "Share this file with Gemini for architecture analysis"
echo ""
