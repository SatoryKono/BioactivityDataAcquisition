#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"
EXPECTED_MEMORY_PATH="${REPO_ROOT}/docs/00-project/ai/memory/mcp-memory.json"

ok() {
  printf "[OK] %s\n" "$1"
}

warn() {
  printf "[WARN] %s\n" "$1"
}

fail() {
  printf "[FAIL] %s\n" "$1" >&2
}

require_contains() {
  local text="$1"
  local pattern="$2"
  local message="$3"
  if grep -Fq -- "$pattern" <<<"$text"; then
    ok "$message"
  else
    fail "$message"
    return 1
  fi
}

if ! command -v codex >/dev/null 2>&1; then
  fail "codex CLI not found in PATH"
  exit 1
fi

status=0

list_out="$(codex mcp list 2>&1 || true)"
if grep -Eq "No MCP servers configured|Error:" <<<"$list_out"; then
  fail "Unable to read MCP server list"
  printf "%s\n" "$list_out" >&2
  exit 1
fi

printf "=== MCP server list ===\n%s\n\n" "$list_out"

for server in memory filesystem sequential-thinking github; do
  if grep -Eq "^${server}[[:space:]]" <<<"$list_out"; then
    ok "Server '${server}' is registered"
  else
    fail "Server '${server}' is missing"
    status=1
  fi
done

memory_out="$(codex mcp get memory 2>&1 || true)"
filesystem_out="$(codex mcp get filesystem 2>&1 || true)"
sequential_out="$(codex mcp get sequential-thinking 2>&1 || true)"
github_out="$(codex mcp get github 2>&1 || true)"

require_contains "$memory_out" "@modelcontextprotocol/server-memory@2026.1.26" "memory is pinned to @2026.1.26" || status=1
require_contains "$filesystem_out" "@modelcontextprotocol/server-filesystem@2026.1.14" "filesystem is pinned to @2026.1.14" || status=1
require_contains "$sequential_out" "@modelcontextprotocol/server-sequential-thinking@2025.12.18" "sequential-thinking is pinned to @2025.12.18" || status=1
require_contains "$github_out" "@modelcontextprotocol/server-github@2025.4.8" "github is pinned to @2025.4.8" || status=1

if grep -Fq -- "${REPO_ROOT}" <<<"$filesystem_out"; then
  ok "filesystem scope is restricted to repo root"
else
  fail "filesystem scope is not restricted to ${REPO_ROOT}"
  status=1
fi

if [[ -f "$EXPECTED_MEMORY_PATH" ]]; then
  ok "memory file exists at ${EXPECTED_MEMORY_PATH}"
else
  fail "memory file missing at ${EXPECTED_MEMORY_PATH}"
  status=1
fi

if [[ -n "${GITHUB_PERSONAL_ACCESS_TOKEN:-}" ]]; then
  ok "GITHUB_PERSONAL_ACCESS_TOKEN is set"
else
  warn "GITHUB_PERSONAL_ACCESS_TOKEN is not set (GitHub MCP auth may fail)"
fi

exit "$status"
