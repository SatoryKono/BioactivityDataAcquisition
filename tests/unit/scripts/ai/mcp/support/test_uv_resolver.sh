#!/usr/bin/env bash
# Tests for uv_resolver.sh uv/uvx resolution logic.

set -euo pipefail

# Source the resolver functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../../.." && pwd)"
# shellcheck source=/dev/null
source "${REPO_ROOT}/scripts/ai/mcp/support/uv_resolver.sh"

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Test helpers
test_passed() {
  echo "✓ $1"
  ((TESTS_PASSED++))
  ((TESTS_RUN++))
}

test_failed() {
  echo "✗ $1"
  ((TESTS_FAILED++))
  ((TESTS_RUN++))
}

# Mock functions for testing
command() {
  if [[ "$1" == "uvx" ]]; then
    return 0
  fi
  return 1
}

dirname() {
  echo "/usr/bin"
}

# Test: bioetl_enable_uvx_network_bypass is opt-in
test_network_bypass_opt_in() {
  # Test default behavior (no bypass)
  unset BIOETL_UVX_DIRECT_NETWORK
  export HTTP_PROXY="http://proxy.example.com"
  bioetl_enable_uvx_network_bypass
  if [[ "${HTTP_PROXY:-}" == "http://proxy.example.com" ]]; then
    test_passed "network_bypass_opt_in: preserves proxy when opt-in not set"
  else
    test_failed "network_bypass_opt_in: should preserve proxy when opt-in not set"
  fi
  unset HTTP_PROXY
}

# Test: bioetl_enable_uvx_network_bypass with opt-in
test_network_bypass_with_opt_in() {
  export BIOETL_UVX_DIRECT_NETWORK="1"
  export HTTP_PROXY="http://proxy.example.com"
  bioetl_enable_uvx_network_bypass
  if [[ "${HTTP_PROXY:-}" == "" ]]; then
    test_passed "network_bypass_with_opt_in: removes proxy when opt-in set"
  else
    test_failed "network_bypass_with_opt_in: should remove proxy when opt-in set"
  fi
  unset BIOETL_UVX_DIRECT_NETWORK
  unset HTTP_PROXY
}

# Test: bioetl_resolve_uvx_bin returns uvx when on PATH
test_resolve_uvx_on_path() {
  result=$(bioetl_resolve_uvx_bin)
  if [[ "${result}" == "/usr/bin/uvx" ]]; then
    test_passed "resolve_uvx_on_path: returns uvx when on PATH"
  else
    test_failed "resolve_uvx_on_path: should return uvx when on PATH"
  fi
}

# Test: bioetl_resolve_uvx_bin handles unset HOME
test_resolve_uvx_unset_home() {
  unset HOME
  # This should not fail with set -u
  result=$(bioetl_resolve_uvx_bin 2>&1 || true)
  if [[ "${result}" == "uvx" ]]; then
    test_passed "resolve_uvx_unset_home: handles unset HOME gracefully"
  else
    test_failed "resolve_uvx_unset_home: should handle unset HOME gracefully"
  fi
}

# Test: bioetl_resolve_uvx_bin uses HOME:- for safety
test_resolve_uvx_home_default() {
  export HOME="/home/test"
  result=$(bioetl_resolve_uvx_bin 2>&1 || true)
  # Should not error even if paths don't exist
  if [[ -n "${result}" ]]; then
    test_passed "resolve_uvx_home_default: uses HOME:- safely"
  else
    test_failed "resolve_uvx_home_default: should use HOME:- safely"
  fi
  unset HOME
}

# Run tests
echo "Running uv_resolver.sh tests..."
echo ""

test_network_bypass_opt_in
test_network_bypass_with_opt_in
test_resolve_uvx_on_path
test_resolve_uvx_unset_home
test_resolve_uvx_home_default

echo ""
echo "Test Results:"
echo "  Run: ${TESTS_RUN}"
echo "  Passed: ${TESTS_PASSED}"
echo "  Failed: ${TESTS_FAILED}"

if [[ ${TESTS_FAILED} -gt 0 ]]; then
  exit 1
fi
exit 0
