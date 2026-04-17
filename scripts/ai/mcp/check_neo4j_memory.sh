#!/usr/bin/env bash
# Final verification script for Neo4j Memory MCP setup
# Checks: MCP registration + Neo4j backend connectivity

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../.." && pwd)"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

ok() {
  local message="${1:-}"
  printf "${GREEN}[✓]${NC} %s\n" "$message"
  return 0
}

warn() {
  local message="${1:-}"
  printf "${YELLOW}[⚠]${NC} %s\n" "$message"
  return 0
}

fail() {
  local message="${1:-}"
  printf "${RED}[✗]${NC} %s\n" "$message" >&2
  return 0
}

info() {
  local message="${1:-}"
  printf "${BLUE}[i]${NC} %s\n" "$message"
  return 0
}

section() {
  local message="${1:-}"
  printf "\n${BLUE}=== %s ===${NC}\n" "$message"
  return 0
}

# shellcheck source=./support/load_repo_env.sh
source "${SCRIPT_DIR}/support/load_repo_env.sh"
load_repo_env_if_present

status=0
INDENT_SED='s/^/  /'
NEO4J_CONTAINER_NAME='bioetl-neo4j'

section "Neo4j Memory MCP Verification"

# Check 1: codex CLI availability
info "Checking Codex CLI..."
if ! command -v codex >/dev/null 2>&1; then
  fail "codex CLI not found in PATH"
  exit 1
fi
ok "Codex CLI available"

# Check 2: MCP server registration
info "Checking MCP server registration..."
list_out="$(codex mcp list 2>&1 || true)"

if grep -Eq "No MCP servers configured|Error:" <<<"$list_out"; then
  fail "Unable to read MCP server list"
  printf "%s\n" "$list_out" >&2
  exit 1
fi

info "Registered MCP servers:"
printf "%s\n" "$list_out" | sed "$INDENT_SED"

if grep -Eq "^neo4j-memory[[:space:]]" <<<"$list_out"; then
  ok "neo4j-memory server is registered"
else
  fail "neo4j-memory server is NOT registered"
  status=1
fi

# Check 3: neo4j-memory configuration
info "Checking neo4j-memory configuration..."
neo4j_config="$(codex mcp get neo4j-memory 2>&1 || true)"
printf "%s\n" "$neo4j_config" | sed "$INDENT_SED"

if grep -Fq "mcp_neo4j_memory_wrapper" <<<"$neo4j_config"; then
  ok "neo4j-memory uses correct wrapper script"
else
  fail "neo4j-memory wrapper not found in configuration"
  status=1
fi

# Check 4: Neo4j Backend Connectivity
section "Neo4j Backend Status"

NEO4J_URI="${NEO4J_URI:-bolt://localhost:7687}"
NEO4J_USERNAME="${NEO4J_USERNAME:-${NEO4J_AUTH_USERNAME:-neo4j}}"
NEO4J_PASSWORD="${NEO4J_PASSWORD:-${NEO4J_AUTH_PASSWORD:-bioetl_secure_password}}"

info "Configured Neo4j URI: $NEO4J_URI"
info "Configured username: $NEO4J_USERNAME"

# Extract host and port from bolt URI
NEO4J_HOST=$(echo "$NEO4J_URI" | sed -E 's|^bolt://([^:/]+).*|\1|')
NEO4J_PORT=$(echo "$NEO4J_URI" | sed -E 's|.*:([0-9]+).*|\1|')

info "Checking port availability: $NEO4J_HOST:$NEO4J_PORT"

# Try to connect to port using nc or netstat
if command -v nc >/dev/null 2>&1; then
  if nc -z "$NEO4J_HOST" "$NEO4J_PORT" 2>/dev/null; then
    ok "Neo4j port $NEO4J_PORT is open"
  else
    fail "Neo4j port $NEO4J_PORT is NOT open (Neo4j backend may not be running)"
    warn "To start Neo4j, run:"
    printf "  ${BLUE}docker run -d --name bioetl-neo4j \\${NC}\n"
    printf "    ${BLUE}-p 7474:7474 -p 7687:7687 \\${NC}\n"
    printf "    ${BLUE}-e NEO4J_AUTH=neo4j/bioetl_secure_password \\${NC}\n"
    printf "    ${BLUE}neo4j:5.15-community${NC}\n"
    status=1
  fi
elif command -v timeout >/dev/null 2>&1; then
  if timeout 2 bash -c "echo >/dev/tcp/$NEO4J_HOST/$NEO4J_PORT" 2>/dev/null; then
    ok "Neo4j port $NEO4J_PORT is open"
  else
    fail "Neo4j port $NEO4J_PORT is NOT open (Neo4j backend may not be running)"
    warn "To start Neo4j, run:"
    printf "  ${BLUE}docker run -d --name bioetl-neo4j \\${NC}\n"
    printf "    ${BLUE}-p 7474:7474 -p 7687:7687 \\${NC}\n"
    printf "    ${BLUE}-e NEO4J_AUTH=neo4j/bioetl_secure_password \\${NC}\n"
    printf "    ${BLUE}neo4j:5.15-community${NC}\n"
    status=1
  fi
else
  warn "Cannot check port connectivity (nc and timeout not available)"
fi

# Check 5: Docker container status (if available)
section "Docker Container Status"

if command -v docker >/dev/null 2>&1; then
  info "Checking Docker containers..."
  
  if docker ps | grep -q "$NEO4J_CONTAINER_NAME"; then
    ok "Neo4j container is RUNNING"
    docker ps | grep "$NEO4J_CONTAINER_NAME" | sed "$INDENT_SED"
  elif docker ps -a | grep -q "$NEO4J_CONTAINER_NAME"; then
    fail "Neo4j container EXISTS but is NOT RUNNING"
    docker ps -a | grep "$NEO4J_CONTAINER_NAME" | sed "$INDENT_SED"
    warn "To start the container:"
    printf "  ${BLUE}docker start bioetl-neo4j${NC}\n"
  else
    warn "Neo4j container does not exist"
    warn "To create and start it, run:"
    printf "  ${BLUE}docker run -d --name bioetl-neo4j \\${NC}\n"
    printf "    ${BLUE}-p 7474:7474 -p 7687:7687 \\${NC}\n"
    printf "    ${BLUE}-e NEO4J_AUTH=neo4j/bioetl_secure_password \\${NC}\n"
    printf "    ${BLUE}neo4j:5.15-community${NC}\n"
  fi
else
  warn "Docker not available in this environment"
fi

# Check 6: Environment Configuration
section "Environment Configuration"

if [[ -n "${NEO4J_AUTH:-}" ]]; then
  ok "NEO4J_AUTH is set"
else
  warn "NEO4J_AUTH is not set (using defaults)"
fi

if [[ -f "${REPO_ROOT}/.env" ]]; then
  ok ".env file exists"
  if grep -Fq "NEO4J_" "${REPO_ROOT}/.env"; then
    ok ".env contains Neo4j configuration"
  else
    warn ".env file does not contain Neo4j settings"
  fi
else
  warn ".env file does not exist (using .env.example defaults)"
fi

# Check 7: Memory file
section "Memory Storage"

EXPECTED_MEMORY_PATH="${REPO_ROOT}/docs/00-project/ai/memory/mcp-memory.json"
if [[ -f "$EXPECTED_MEMORY_PATH" ]]; then
  ok "Memory file exists at: $EXPECTED_MEMORY_PATH"
  memory_size=$(wc -c < "$EXPECTED_MEMORY_PATH")
  info "Memory file size: $memory_size bytes"
else
  warn "Memory file missing at: $EXPECTED_MEMORY_PATH"
  info "Will be created on first MCP use"
fi

# Summary
section "Summary"

if [[ $status -eq 0 ]]; then
  ok "All checks passed!"
  printf "\n${GREEN}Next steps:${NC}\n"
  printf "  1. Open Neo4j Browser: http://localhost:7474/browser/\n"
  printf "  2. Use Codex MCP: codex mcp get neo4j-memory\n"
  printf "  3. Test queries through your AI interface\n"
else
  fail "Some checks failed"
  printf "\n${YELLOW}To complete setup:${NC}\n"
  printf "  1. Start Neo4j backend:\n"
  printf "     ${BLUE}docker run -d --name bioetl-neo4j \\${NC}\n"
  printf "       ${BLUE}-p 7474:7474 -p 7687:7687 \\${NC}\n"
  printf "       ${BLUE}-e NEO4J_AUTH=neo4j/bioetl_secure_password \\${NC}\n"
  printf "       ${BLUE}neo4j:5.15-community${NC}\n"
  printf "  2. Re-run this check:\n"
  printf "     ${BLUE}bash scripts/ai/mcp/check_neo4j_memory.sh${NC}\n"
fi

exit "$status"
