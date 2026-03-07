#!/usr/bin/env bash
# ============================================================
# BioETL Test Runner
# Usage: ./scripts/dev/run_tests.sh [command] [options]
# ============================================================
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$PROJECT_DIR"

# --- Detect Python ---
# On Windows (Git Bash / MSYS2), prefer `py` launcher which finds the correct
# Python installation. Avoid /usr/bin/python3 (MSYS2 stub without project packages).
detect_python() {
    local cmd
    for cmd in py python python3; do
        if command -v "$cmd" >/dev/null 2>&1 && "$cmd" -c "import pytest" >/dev/null 2>&1; then
            echo "$cmd"
            return 0
        fi
    done
    return 1
}
PYTHON="$(detect_python)" || {
    echo "ERROR: Python with pytest not found in PATH" >&2
    echo "Install: pip install pytest" >&2
    exit 1
}

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}[INFO]${NC} $*"; }
ok()    { echo -e "${GREEN}[OK]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
err()   { echo -e "${RED}[FAIL]${NC} $*"; }

usage() {
    cat <<EOF
BioETL Test Runner

Usage: $(basename "$0") <command> [pytest-args...]

Commands:
  all           Run all tests (stop on first failure)
  unit          Unit tests only (tests/unit/)
  arch          Architecture tests (tests/architecture/)
  integration   Integration tests (tests/integration/)
  contract      Contract tests (tests/contract/)
  contract-live Contract tests with live APIs + network enabled
  smoke         Smoke tests (tests/smoke/)
  security      Security tests (tests/security/)
  cov           All tests with coverage report (fail-under=85%)
  quick         Unit + smoke (fast feedback loop)
  parallel      All tests via pytest-xdist (-n auto)
  marker <m>    Run tests by marker, e.g.: marker slow
  failed        Re-run only failed tests from last run
  file <path>   Run a specific test file
  help          Show this message

Options:
  Any extra arguments are passed directly to pytest.

Examples:
  $(basename "$0") unit
  $(basename "$0") unit -k "test_transformer"
  $(basename "$0") cov --cov-report=term-missing
  $(basename "$0") marker hypothesis
  $(basename "$0") file tests/unit/domain/test_entities.py -v
  $(basename "$0") all --tb=short
EOF
}

run_pytest() {
    local label="$1"; shift
    info "Running: ${label}"
    info "Command: ${PYTHON} -m pytest $*"
    echo ""
    if "$PYTHON" -m pytest "$@"; then
        echo ""
        ok "${label} passed"
    else
        echo ""
        err "${label} failed"
        exit 1
    fi
}

# --- Commands ---
cmd_all()         { run_pytest "All Tests"         tests/ -x -q "$@"; }
cmd_unit()        { run_pytest "Unit Tests"         tests/unit/ -x -q "$@"; }
cmd_arch()        { run_pytest "Architecture Tests" tests/architecture/ -v "$@"; }
cmd_integration() { run_pytest "Integration Tests"  tests/integration/ -x -q "$@"; }
cmd_contract()    { run_pytest "Contract Tests"     tests/contract/ -v "$@"; }
cmd_contract_live() {
    info "Running: Contract Tests (live APIs + network)"
    info "Command: BIOETL_LIVE_API_TESTS=true BIOETL_NETWORK_TESTS=true ${PYTHON} -m pytest tests/contract/ --network -v $*"
    echo ""
    if BIOETL_LIVE_API_TESTS=true BIOETL_NETWORK_TESTS=true "$PYTHON" -m pytest tests/contract/ --network -v "$@"; then
        echo ""
        ok "Contract Tests (live) passed"
    else
        echo ""
        err "Contract Tests (live) failed"
        exit 1
    fi
}
cmd_smoke()       { run_pytest "Smoke Tests"        tests/smoke/ -v "$@"; }
cmd_security()    { run_pytest "Security Tests"     tests/security/ -v "$@"; }

cmd_cov() {
    run_pytest "Tests + Coverage" tests/ \
        --cov=src/bioetl \
        --cov-report=html \
        --cov-report=term-missing \
        --cov-fail-under=85 \
        -q "$@"
    ok "HTML report: htmlcov/index.html"
}

cmd_quick() {
    info "Quick check: unit + smoke"
    run_pytest "Unit Tests"  tests/unit/ -x -q "$@"
    run_pytest "Smoke Tests" tests/smoke/ -x -q "$@"
}

cmd_parallel() {
    run_pytest "All Tests (parallel)" tests/ -n auto -q "$@"
}

cmd_marker() {
    if [[ $# -lt 1 ]]; then
        err "Usage: $(basename "$0") marker <marker-name> [pytest-args...]"
        echo "Available markers: unit, integration, e2e, slow, hypothesis, security,"
        echo "  vcr, performance, architecture, contracts, benchmark, smoke, serial"
        exit 1
    fi
    local marker="$1"; shift
    run_pytest "Marker: ${marker}" tests/ -m "$marker" -v "$@"
}

cmd_failed()  { run_pytest "Re-run Failed"    tests/ --lf -x -v "$@"; }

cmd_file() {
    if [[ $# -lt 1 ]]; then
        err "Usage: $(basename "$0") file <path> [pytest-args...]"
        exit 1
    fi
    local file="$1"; shift
    run_pytest "File: ${file}" "$file" -v "$@"
}

# --- Main ---
if [[ $# -lt 1 ]]; then
    usage
    exit 0
fi

command="$1"; shift

case "$command" in
    all)         cmd_all "$@" ;;
    unit)        cmd_unit "$@" ;;
    arch)        cmd_arch "$@" ;;
    integration) cmd_integration "$@" ;;
    contract)    cmd_contract "$@" ;;
    contract-live) cmd_contract_live "$@" ;;
    smoke)       cmd_smoke "$@" ;;
    security)    cmd_security "$@" ;;
    cov)         cmd_cov "$@" ;;
    quick)       cmd_quick "$@" ;;
    parallel)    cmd_parallel "$@" ;;
    marker)      cmd_marker "$@" ;;
    failed)      cmd_failed "$@" ;;
    file)        cmd_file "$@" ;;
    help|--help|-h) usage ;;
    *)
        err "Unknown command: ${command}"
        usage
        exit 1
        ;;
esac
