#!/bin/bash

# lib/tasks/review.sh - Code review task

# Calculate paths - use passed PROJECT_ROOT if available
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -z "$PROJECT_ROOT" ]; then
  # Fallback: go up 4 levels from lib/tasks/ to project root
  PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"
fi

export PROJECT_ROOT

source "${SCRIPT_DIR}/../utils.sh"

SCOPE="${1:-staged}"
FOCUS="${2:-all}"
SESSIONS_DIR=$(get_sessions_dir)

mkdir -p "$SESSIONS_DIR"

TASK_FILE="${SESSIONS_DIR}/review-$(date +%s).md"

print_header
print_section "Code Review Task"

case "$SCOPE" in
  staged)
    echo "Scope: Staged changes (git diff --staged)"
    ;;
  file)
    FILE_PATH=$(sanitize_path "$3")
    echo "Scope: $FILE_PATH"
    ;;
  directory|dir)
    DIR_PATH=$(sanitize_path "$3")
    echo "Scope: $DIR_PATH"
    ;;
  project)
    echo "Scope: Entire project"
    ;;
  *)
    print_error "Unknown scope: $SCOPE"
    echo "Valid scopes: staged, file, directory, project"
    exit 1
    ;;
esac

cat > "$TASK_FILE" << EOF
# Code Review Task

**Profile:** py-review-orchestrator  
**Role:** default (orchestration)  
**Created:** $(date)  
**Scope:** ${SCOPE}  
**Focus:** ${FOCUS}  

## Task Description

Review code against BioETL standards defined in GEMINI.md:
- Architecture compliance (hexagonal pattern)
- Test coverage (≥85%)
- Type hints and mypy strictness
- Logging (structlog, no print)
- Error handling patterns

## Focus Areas
${FOCUS}

## Context Files
- GEMINI.md (project constraints)
- .gemini/agents/py-review-orchestrator.md (agent profile)
- .codex/agents/CODEX-RUNTIME.md (reference)

---

## Review Results

[Gemini output will be appended here]

EOF

print_success "Task file created"
print_info "File: $TASK_FILE"
echo ""
print_info "Share this file with Gemini along with GEMINI.md for full code review"
echo ""
