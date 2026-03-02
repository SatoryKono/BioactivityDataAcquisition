#!/usr/bin/env bash
# run-tests.sh - Test runner script for BioETL
# Usage: ./scripts/run-tests.sh [options]
#
# Options:
#   --unit          Run only unit tests
#   --integration   Run only integration tests
#   --architecture  Run only architecture tests
#   --coverage      Run with coverage report (default)
#   --fast          Run in parallel mode (faster)
#   --no-cov        Skip coverage calculation
#   --help          Show this help message

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

show_help() {
    echo "BioETL Test Runner"
    echo ""
    echo "Usage: ./scripts/run-tests.sh [options]"
    echo ""
    echo "Options:"
    echo "  --unit          Run only unit tests"
    echo "  --integration   Run only integration tests"
    echo "  --architecture  Run only architecture tests"
    echo "  --coverage      Run with coverage report (default)"
    echo "  --fast          Run in parallel mode (faster)"
    echo "  --no-cov        Skip coverage calculation"
    echo "  --help          Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./scripts/run-tests.sh                    # Run all tests with coverage"
    echo "  ./scripts/run-tests.sh --unit --fast      # Run unit tests in parallel"
    echo "  ./scripts/run-tests.sh --architecture     # Run architecture tests only"
}

# Detect Python runner (uv or venv)
detect_runner() {
    if command -v uv &> /dev/null && [[ -f "uv.lock" ]]; then
        echo "uv run"
    elif [[ -f ".venv/bin/python" ]]; then
        echo ".venv/bin/python -m"
    elif [[ -f ".venv/Scripts/python.exe" ]]; then
        echo ".venv/Scripts/python -m"
    else
        log_error "No Python environment found. Run ./scripts/setup.sh first."
        exit 1
    fi
}

# Main
main() {
    # Parse arguments
    TEST_TYPE="all"
    COVERAGE=true
    PARALLEL=false
    EXTRA_ARGS=""

    while [[ $# -gt 0 ]]; do
        case $1 in
            --unit)
                TEST_TYPE="unit"
                shift
                ;;
            --integration)
                TEST_TYPE="integration"
                shift
                ;;
            --architecture)
                TEST_TYPE="architecture"
                shift
                ;;
            --coverage)
                COVERAGE=true
                shift
                ;;
            --no-cov)
                COVERAGE=false
                shift
                ;;
            --fast)
                PARALLEL=true
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                EXTRA_ARGS="$EXTRA_ARGS $1"
                shift
                ;;
        esac
    done

    RUNNER=$(detect_runner)
    log_info "Using runner: $RUNNER"

    # Build pytest command
    PYTEST_CMD="$RUNNER pytest"
    PYTEST_ARGS="-v"

    # Add test path based on type
    case $TEST_TYPE in
        unit)
            PYTEST_ARGS="$PYTEST_ARGS tests/unit/ -m unit"
            log_info "Running unit tests..."
            ;;
        integration)
            PYTEST_ARGS="$PYTEST_ARGS tests/integration/ -m integration --vcr-record=none"
            log_info "Running integration tests..."
            ;;
        architecture)
            PYTEST_ARGS="$PYTEST_ARGS tests/architecture/"
            log_info "Running architecture tests..."
            ;;
        all)
            PYTEST_ARGS="$PYTEST_ARGS tests/ -m 'not e2e'"
            log_info "Running all tests (excluding e2e)..."
            ;;
    esac

    # Add coverage options
    if [[ "$COVERAGE" == true ]]; then
        PYTEST_ARGS="$PYTEST_ARGS --cov=src/bioetl --cov-report=term-missing --cov-fail-under=85"
    fi

    # Add parallel options
    if [[ "$PARALLEL" == true ]]; then
        PYTEST_ARGS="$PYTEST_ARGS -n auto --dist loadscope"
    fi

    # Add extra args
    PYTEST_ARGS="$PYTEST_ARGS $EXTRA_ARGS"

    # Run tests
    log_info "Command: $PYTEST_CMD $PYTEST_ARGS"
    echo ""

    if $PYTEST_CMD $PYTEST_ARGS; then
        log_success "All tests passed!"
    else
        log_error "Tests failed!"
        exit 1
    fi
}

main "$@"
