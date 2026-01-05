#!/usr/bin/env bash
# test_changed.sh - Run tests for changed files only
# Usage: ./scripts/test_changed.sh [base_branch]
#
# This script identifies changed Python files and runs related tests.
# Useful for quick feedback during development.

set -euo pipefail

# Colors for output
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

# Base branch to compare against (default: main)
BASE_BRANCH="${1:-main}"

# Detect Python runner
detect_runner() {
    if command -v uv &> /dev/null && [[ -f "uv.lock" ]]; then
        echo "uv run"
    elif [[ -f ".venv/bin/python" ]]; then
        echo ".venv/bin/python -m"
    else
        echo "python -m"
    fi
}

RUNNER=$(detect_runner)

# Get changed Python files in src/bioetl/
CHANGED_SRC=$(git diff --name-only "${BASE_BRANCH}"...HEAD 2>/dev/null | grep "^src/bioetl.*\.py$" || true)

if [[ -z "$CHANGED_SRC" ]]; then
    # No source changes, check for test changes
    CHANGED_TESTS=$(git diff --name-only "${BASE_BRANCH}"...HEAD 2>/dev/null | grep "^tests/.*\.py$" || true)

    if [[ -z "$CHANGED_TESTS" ]]; then
        log_info "No Python changes detected. Running smoke tests..."
        HYPOTHESIS_PROFILE=fast $RUNNER pytest tests/unit/ -m "not slow" -n auto --dist loadscope -q --tb=short
        exit $?
    else
        log_info "Only test files changed. Running changed tests..."
        echo "$CHANGED_TESTS" | xargs $RUNNER pytest -v --tb=short
        exit $?
    fi
fi

log_info "Changed source files:"
echo "$CHANGED_SRC" | sed 's/^/  /'
echo ""

# Convert source paths to module patterns for test discovery
# src/bioetl/domain/types.py -> domain_types or types
TEST_KEYWORDS=""
while IFS= read -r file; do
    # Extract module name without extension
    module=$(basename "$file" .py)
    # Add to keywords (pytest -k uses OR for multiple keywords)
    if [[ -n "$TEST_KEYWORDS" ]]; then
        TEST_KEYWORDS="$TEST_KEYWORDS or $module"
    else
        TEST_KEYWORDS="$module"
    fi
done <<< "$CHANGED_SRC"

log_info "Running tests matching: $TEST_KEYWORDS"
echo ""

# Run tests with fast profile for quick feedback
HYPOTHESIS_PROFILE=fast $RUNNER pytest tests/ \
    -k "$TEST_KEYWORDS" \
    -n auto --dist loadscope \
    -v --tb=short \
    --ignore=tests/e2e/ \
    --ignore=tests/benchmarks/ \
    || {
        log_warn "Some keyword-based tests failed or none matched. Running all unit tests..."
        HYPOTHESIS_PROFILE=fast $RUNNER pytest tests/unit/ -m "not slow" -n auto --dist loadscope -q --tb=short
    }

log_success "Tests completed!"
