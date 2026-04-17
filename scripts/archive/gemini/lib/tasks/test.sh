#!/bin/bash

# lib/tasks/test.sh - Test generation task

# Calculate paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -z "$PROJECT_ROOT" ]; then
  PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"
fi

export PROJECT_ROOT

source "${SCRIPT_DIR}/../utils.sh"

COVERAGE="${1:-85}"
SCOPE="${2:-application}"
SESSIONS_DIR=$(get_sessions_dir)

mkdir -p "$SESSIONS_DIR"

TASK_FILE="${SESSIONS_DIR}/test-gen-$(date +%s).md"

print_header
print_section "Test Generation Task"

echo "Target coverage: ${COVERAGE}%"
echo "Scope: ${SCOPE}"

case "$SCOPE" in
  application|domain|all) ;;
  *)
    print_error "Unknown scope: $SCOPE"
    echo "Valid scopes: application, domain, all"
    exit 1
    ;;
esac

cat > "$TASK_FILE" << EOF
# Test Generation Task

**Profile:** py-test-swarm  
**Role:** default (orchestration)  
**Created:** $(date)  
**Target Coverage:** ${COVERAGE}%  
**Scope:** ${SCOPE}  

## Task Description

Generate missing unit and integration tests using pytest:
- Unit tests for domain logic
- Integration tests for adapters
- VCR cassettes for HTTP calls
- Fixtures with in-memory fakes

## Requirements
- Achieve ${COVERAGE}% coverage in src/bioetl/${SCOPE}
- All tests in tests/ directory
- Fixtures in tests/fixtures/
- HTTP cassettes in tests/fixtures/vcr/{provider}/

## Context
- GEMINI.md (section 5: Testing & Validation)
- .gemini/agents/py-test-swarm.md
- pytest.ini (test configuration)

---

## Generated Tests

[Gemini output will be appended here]

EOF

print_success "Task file created"
print_info "File: $TASK_FILE"
echo ""
print_info "Share this file with Gemini for test generation"
echo ""
