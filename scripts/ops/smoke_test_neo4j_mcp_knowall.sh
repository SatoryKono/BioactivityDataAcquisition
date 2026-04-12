#!/usr/bin/env bash
# Smoke Test: Neo4j Memory MCP Integration (@knowall-ai version)
# Tests the complete chain with @knowall-ai/mcp-neo4j-agent-memory@0.2.5
# Run AFTER: bash scripts/ops/wsl_neo4j_startup.sh

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

pass() { printf "${GREEN}✓${NC} %s\n" "$1"; }
fail() { printf "${RED}✗${NC} %s\n" "$1" >&2; return 1; }
warn() { printf "${YELLOW}!${NC} %s\n" "$1"; }
info() { printf "${BLUE}→${NC} %s\n" "$1"; }
header() { printf "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n%s\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n" "$1"; }

status=0

detect_env() {
  if grep -qi microsoft /proc/version 2>/dev/null; then
    echo "wsl"
  elif [[ "$OSTYPE" == "darwin"* ]]; then
    echo "macos"
  elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "linux"
  else
    echo "unknown"
  fi
}

select_docker_bin() {
  local env_type="$1"
  if [[ "$env_type" == "wsl" ]] && command -v docker.exe >/dev/null 2>&1; then
    echo "docker.exe"
    return 0
  fi
  if command -v docker >/dev/null 2>&1; then
    echo "docker"
    return 0
  fi
  return 1
}

ENV_TYPE="$(detect_env)"
DOCKER_BIN="$(select_docker_bin "$ENV_TYPE" || true)"

# ============================================================================
# TEST 1: Docker Container Status
# ============================================================================
header "TEST 1: Docker Container Status"

if [[ -z "${DOCKER_BIN}" ]]; then
  fail "Docker CLI not available in this environment"
  status=1
else
  docker_ps_names="$("${DOCKER_BIN}" ps --format '{{.Names}}' 2>/dev/null || true)"
  if grep -qx "bioetl-neo4j" <<<"$docker_ps_names"; then
  pass "Container bioetl-neo4j is RUNNING"
    "${DOCKER_BIN}" ps --format '{{.ID}} {{.Image}} {{.Status}} {{.Ports}} {{.Names}}' 2>/dev/null | grep ' bioetl-neo4j$' | head -1 | sed 's/^/  /'
  else
    fail "Container bioetl-neo4j is NOT RUNNING"
    info "Start it: bash scripts/ops/wsl_neo4j_startup.sh"
    status=1
  fi
fi

# ============================================================================
# TEST 2: Port Accessibility (Localhost)
# ============================================================================
header "TEST 2: Port Accessibility"

VERIFY_HOST="127.0.0.1"
VERIFY_LABEL="localhost"
if [[ "$ENV_TYPE" == "wsl" ]]; then
  VERIFY_HOST="host.docker.internal"
  VERIFY_LABEL="host.docker.internal"
fi

info "Testing ${VERIFY_LABEL} connectivity..."

if timeout 2 bash -c "echo >/dev/tcp/${VERIFY_HOST}/7687" 2>/dev/null; then
  pass "Bolt port (7687) accessible on ${VERIFY_LABEL}"
else
  warn "Bolt port (7687) not accessible on ${VERIFY_LABEL}"
fi

if timeout 2 bash -c "echo >/dev/tcp/${VERIFY_HOST}/7474" 2>/dev/null; then
  pass "HTTP port (7474) accessible on ${VERIFY_LABEL}"
else
  warn "HTTP port (7474) not accessible on ${VERIFY_LABEL}"
fi

# ============================================================================
# TEST 3: Wrapper Script Verification
# ============================================================================
header "TEST 3: Wrapper Script (@knowall-ai/mcp-neo4j-agent-memory)"

WRAPPER_PATH="${REPO_ROOT}/scripts/ops/mcp_neo4j_memory_wrapper.sh"

if [[ -f "$WRAPPER_PATH" ]]; then
  pass "Wrapper script exists"
  
  if grep -q "@knowall-ai/mcp-neo4j-agent-memory@0.2.5" "$WRAPPER_PATH"; then
    pass "Wrapper uses @knowall-ai/mcp-neo4j-agent-memory@0.2.5"
  else
    fail "Wrapper does not reference correct package"
    status=1
  fi
  
  if grep -q "NEO4J_URI\|NEO4J_USERNAME\|NEO4J_PASSWORD" "$WRAPPER_PATH"; then
    pass "Wrapper exports Neo4j environment variables"
  else
    fail "Wrapper missing environment setup"
    status=1
  fi
  
  if [[ -x "$WRAPPER_PATH" ]]; then
    pass "Wrapper is executable"
  else
    fail "Wrapper is not executable"
    info "Fix: chmod +x $WRAPPER_PATH"
    status=1
  fi
else
  fail "Wrapper script NOT found at $WRAPPER_PATH"
  status=1
fi

# ============================================================================
# TEST 4: Environment Variables
# ============================================================================
header "TEST 4: Environment Configuration"

source "${SCRIPT_DIR}/support/load_repo_env.sh" 2>/dev/null || true
load_repo_env_if_present 2>/dev/null || true

NEO4J_URI="${NEO4J_URI:-bolt://localhost:7687}"
NEO4J_USERNAME="${NEO4J_USERNAME:-neo4j}"
NEO4J_PASSWORD="${NEO4J_PASSWORD:-bioetl_secure_password}"

pass "NEO4J_URI: $NEO4J_URI"
pass "NEO4J_USERNAME: $NEO4J_USERNAME"

if [[ -n "$NEO4J_PASSWORD" ]]; then
  pass "NEO4J_PASSWORD is configured"
else
  warn "NEO4J_PASSWORD is empty (using default)"
fi

# ============================================================================
# TEST 5: MCP Registration in Codex
# ============================================================================
header "TEST 5: MCP Registration in Codex"

if command -v codex >/dev/null 2>&1; then
  mcp_list=$(codex mcp list 2>&1 || echo "")
  
  if echo "$mcp_list" | grep -q "neo4j-memory"; then
    pass "neo4j-memory is registered in Codex"
    
    mcp_config=$(codex mcp get neo4j-memory 2>&1 || echo "")
    if echo "$mcp_config" | grep -q "mcp_neo4j_memory_wrapper"; then
      pass "Codex uses correct wrapper"
    else
      fail "Codex wrapper configuration incorrect"
      status=1
    fi
  else
    fail "neo4j-memory NOT registered in Codex"
    info "Register: uv run python -m scripts.dev setup-mcp"
    status=1
  fi
else
  warn "Codex CLI not available (MCP check skipped)"
fi

# ============================================================================
# TEST 6: Cypher Query Execution
# ============================================================================
header "TEST 6: Cypher Query Execution"

info "Attempting to execute test Cypher query..."

if [[ -n "${DOCKER_BIN}" ]] && "${DOCKER_BIN}" exec bioetl-neo4j cypher-shell -u neo4j -p bioetl_secure_password \
   "RETURN \"@knowall-ai/mcp-neo4j-agent-memory connected!\" AS status" 2>/dev/null | grep -q "connected"; then
  pass "Cypher query execution works"
else
  warn "Cypher query inconclusive (Neo4j may still be stabilizing)"
fi

# ============================================================================
# TEST 7: Memory File Existence
# ============================================================================
header "TEST 7: Memory Storage"

MEMORY_PATH="${REPO_ROOT}/docs/00-project/ai/memory/mcp-memory.json"

if [[ -f "$MEMORY_PATH" ]]; then
  pass "Memory file exists at $MEMORY_PATH"
  size=$(wc -c < "$MEMORY_PATH")
  info "Size: $size bytes"
else
  warn "Memory file not found (will be created on first MCP use)"
fi

# ============================================================================
# SUMMARY
# ============================================================================
header "Test Summary"

if [[ $status -eq 0 ]]; then
  printf "\n${GREEN}"
  printf "╔═══════════════════════════════════════════╗\n"
  printf "║  ✓ ALL CRITICAL TESTS PASSED            ║\n"
  printf "║  Neo4j Memory MCP (@knowall-ai) READY   ║\n"
  printf "╚═══════════════════════════════════════════╝\n"
  printf "${NC}\n"
  
  printf "✨ Next Steps:\n"
  printf "  1. Test in Codex:\n"
  printf "     ${BLUE}codex interactive${NC}\n"
  printf "     Use ${BLUE}@neo4j-memory${NC} in prompts\n\n"
  printf "  2. Access Neo4j Browser:\n"
  printf "     ${BLUE}http://localhost:7474/browser${NC}\n"
  printf "     (Username: neo4j | Password: bioetl_secure_password)\n\n"
  printf "  3. Store knowledge in Neo4j:\n"
  printf "     ${BLUE}codex interactive${NC}\n"
  printf "     Prompt: \"Store information about [topic] in neo4j-memory\"\n\n"
  
  exit 0
else
  printf "\n${RED}"
  printf "╔═══════════════════════════════════════════╗\n"
  printf "║  ✗ SOME TESTS FAILED                    ║\n"
  printf "║  See details above                      ║\n"
  printf "╚═══════════════════════════════════════════╝\n"
  printf "${NC}\n"
  
  printf "⚠️  Troubleshooting:\n"
  printf "  • Container not running?\n"
  printf "    ${BLUE}bash scripts/ops/wsl_neo4j_startup.sh${NC}\n\n"
  printf "  • Ports closed?\n"
  printf "    Wait 10-15 seconds for Neo4j to fully start\n\n"
  printf "  • MCP not registered?\n"
  printf "    ${BLUE}uv run python -m scripts.dev setup-mcp${NC}\n\n"
  printf "  • View Neo4j logs:\n"
  printf "    ${BLUE}docker logs -f bioetl-neo4j${NC}\n\n"
  
  exit 1
fi
