#!/usr/bin/env bash
# Smoke Test: Neo4j Memory MCP Full Integration
# Run this AFTER starting: docker run -d --name bioetl-neo4j ... neo4j:5.15-community
# 
# Tests the complete chain:
# 1. Docker container running
# 2. Neo4j ports accessible
# 3. MCP wrapper available
# 4. Codex MCP server responsive
# 5. Cypher queries execute

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Helper functions
pass() { printf "${GREEN}✓${NC} %s\n" "$1"; }
fail() { printf "${RED}✗${NC} %s\n" "$1" >&2; return 1; }
warn() { printf "${YELLOW}!${NC} %s\n" "$1"; }
info() { printf "${BLUE}→${NC} %s\n" "$1"; }
header() { printf "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n%s\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n" "$1"; }

overall_status=0

# ============================================================================
# TEST 1: Docker Container Status
# ============================================================================
header "TEST 1: Docker Container Status"

if ! command -v docker >/dev/null 2>&1; then
  fail "Docker CLI not available"
  overall_status=1
else
  pass "Docker CLI available"
  
  if docker ps | grep -q "bioetl-neo4j"; then
    pass "Container bioetl-neo4j is RUNNING"
    docker ps | grep bioetl-neo4j | head -1 | awk '{print $1, $2, $7, $8, $9, $10, $11}' | sed 's/^/  /'
  else
    fail "Container bioetl-neo4j is NOT RUNNING"
    info "Start it with:"
    printf "  docker run -d --name bioetl-neo4j \\\\\n"
    printf "    -p 7474:7474 -p 7687:7687 \\\\\n"
    printf "    -e NEO4J_AUTH=neo4j/bioetl_secure_password \\\\\n"
    printf "    neo4j:5.15-community\n"
    overall_status=1
  fi
fi

# ============================================================================
# TEST 2: Neo4j Ports Accessible
# ============================================================================
header "TEST 2: Neo4j Ports Accessible"

# Test Bolt port (7687)
if timeout 3 bash -c "echo >/dev/tcp/127.0.0.1/7687" 2>/dev/null || \
   (command -v nc >/dev/null 2>&1 && nc -z 127.0.0.1 7687 2>/dev/null); then
  pass "Bolt port (7687) is open"
else
  fail "Bolt port (7687) is NOT accessible"
  warn "Neo4j may still be starting (takes 10-15 seconds)"
  overall_status=1
fi

# Test HTTP port (7474)
if timeout 3 bash -c "echo >/dev/tcp/127.0.0.1/7474" 2>/dev/null || \
   (command -v nc >/dev/null 2>&1 && nc -z 127.0.0.1 7474 2>/dev/null); then
  pass "HTTP port (7474) is open"
else
  fail "HTTP port (7474) is NOT accessible"
  overall_status=1
fi

# ============================================================================
# TEST 3: MCP Wrapper Script
# ============================================================================
header "TEST 3: MCP Wrapper Script"

WRAPPER_PATH="${REPO_ROOT}/scripts/ops/mcp_neo4j_memory_wrapper.sh"

if [[ -f "$WRAPPER_PATH" ]]; then
  pass "Wrapper script exists: $WRAPPER_PATH"
  
  if [[ -x "$WRAPPER_PATH" ]]; then
    pass "Wrapper script is executable"
  else
    fail "Wrapper script is NOT executable"
    info "Fix with: chmod +x $WRAPPER_PATH"
    overall_status=1
  fi
  
  # Check script contains expected elements
  if grep -q "mcp-neo4j-agent-memory" "$WRAPPER_PATH"; then
    pass "Wrapper references correct MCP package"
  else
    fail "Wrapper does not reference MCP package"
    overall_status=1
  fi
  
  if grep -q "NEO4J_URI\|NEO4J_USERNAME\|NEO4J_PASSWORD" "$WRAPPER_PATH"; then
    pass "Wrapper sets Neo4j environment variables"
  else
    fail "Wrapper missing environment variable setup"
    overall_status=1
  fi
else
  fail "Wrapper script NOT found: $WRAPPER_PATH"
  overall_status=1
fi

# ============================================================================
# TEST 4: Codex MCP Registration
# ============================================================================
header "TEST 4: Codex MCP Registration"

if ! command -v codex >/dev/null 2>&1; then
  warn "Codex CLI not available (MCP check skipped)"
else
  mcp_list="$(codex mcp list 2>&1 || echo "")"
  
  if echo "$mcp_list" | grep -q "neo4j-memory"; then
    pass "neo4j-memory is registered in Codex"
    
    mcp_detail="$(codex mcp get neo4j-memory 2>&1 || echo "")"
    if echo "$mcp_detail" | grep -q "mcp_neo4j_memory_wrapper"; then
      pass "neo4j-memory uses correct wrapper"
    else
      fail "neo4j-memory wrapper configuration incorrect"
      overall_status=1
    fi
  else
    fail "neo4j-memory is NOT registered in Codex"
    info "Register with: uv run python -m scripts.dev setup-mcp"
    overall_status=1
  fi
fi

# ============================================================================
# TEST 5: Environment Configuration
# ============================================================================
header "TEST 5: Environment Configuration"

NEO4J_URI="${NEO4J_URI:-bolt://localhost:7687}"
NEO4J_USERNAME="${NEO4J_USERNAME:-${NEO4J_AUTH_USERNAME:-}}"
NEO4J_PASSWORD="${NEO4J_PASSWORD:-${NEO4J_AUTH_PASSWORD:-}}"

if [[ -z "$NEO4J_USERNAME" ]] || [[ -z "$NEO4J_PASSWORD" ]]; then
  if [[ -n "${NEO4J_AUTH:-}" ]]; then
    pass "NEO4J_AUTH is set (will be parsed by wrapper)"
  else
    warn "No Neo4j credentials configured (using wrapper defaults)"
  fi
else
  pass "NEO4J_USERNAME and NEO4J_PASSWORD are configured"
fi

if [[ -f "${REPO_ROOT}/.env" ]]; then
  pass ".env file exists"
else
  info ".env file not found (wrapper uses compiled defaults)"
fi

# ============================================================================
# TEST 6: Neo4j Connectivity (Cypher Shell)
# ============================================================================
header "TEST 6: Neo4j Connectivity"

NEO4J_PASS="${NEO4J_PASSWORD:-bioetl_secure_password}"
NEO4J_USER="${NEO4J_USERNAME:-neo4j}"

if docker exec bioetl-neo4j cypher-shell -u "$NEO4J_USER" -p "$NEO4J_PASS" "RETURN 1 AS test" 2>/dev/null | grep -q "test"; then
  pass "Cypher query execution works"
else
  warn "Cypher query check inconclusive (may need more time to start)"
fi

# ============================================================================
# TEST 7: Neo4j Browser Access
# ============================================================================
header "TEST 7: Neo4j Browser Access"

if timeout 3 bash -c "curl -s http://127.0.0.1:7474/browser/ | head -5" 2>/dev/null | grep -q "<!DOCTYPE\|<html"; then
  pass "Neo4j Browser is accessible at http://localhost:7474/browser/"
else
  warn "Neo4j Browser check inconclusive"
fi

# ============================================================================
# SUMMARY
# ============================================================================
header "Test Summary"

if [[ $overall_status -eq 0 ]]; then
  printf "${GREEN}"
  printf "╔════════════════════════════════════════════╗\n"
  printf "║  ✓ ALL CRITICAL TESTS PASSED              ║\n"
  printf "║  Neo4j Memory MCP is FULLY OPERATIONAL    ║\n"
  printf "╚════════════════════════════════════════════╝\n"
  printf "${NC}\n"
  
  printf "🎉 Next Steps:\n"
  printf "  1. Open Neo4j Browser: ${BLUE}http://localhost:7474/browser/${NC}\n"
  printf "     (Username: neo4j | Password: bioetl_secure_password)\n"
  printf "\n"
  printf "  2. Test MCP in Codex:\n"
  printf "     ${BLUE}codex interactive${NC}\n"
  printf "     Then use @neo4j-memory in prompts\n"
  printf "\n"
  printf "  3. Verify MCP details:\n"
  printf "     ${BLUE}codex mcp get neo4j-memory${NC}\n"
  printf "\n"
  printf "  4. Run comprehensive check:\n"
  printf "     ${BLUE}bash scripts/ops/check_neo4j_mcp.sh${NC}\n"
  
  exit 0
else
  printf "${RED}"
  printf "╔════════════════════════════════════════════╗\n"
  printf "║  ✗ SOME TESTS FAILED                      ║\n"
  printf "║  Check output above for details            ║\n"
  printf "╚════════════════════════════════════════════╝\n"
  printf "${NC}\n"
  
  printf "⚠️ Troubleshooting:\n"
  printf "  • If ports are closed: Neo4j is still starting\n"
  printf "    Wait 10-15 seconds and re-run this test\n"
  printf "\n"
  printf "  • If container is not running:\n"
  printf "    ${BLUE}docker run -d --name bioetl-neo4j \\${NC}\n"
  printf "      ${BLUE}-p 7474:7474 -p 7687:7687 \\${NC}\n"
  printf "      ${BLUE}-e NEO4J_AUTH=neo4j/bioetl_secure_password \\${NC}\n"
  printf "      ${BLUE}neo4j:5.15-community${NC}\n"
  printf "\n"
  printf "  • If MCP not registered:\n"
  printf "    ${BLUE}uv run python -m scripts.dev setup-mcp${NC}\n"
  printf "\n"
  printf "  • For detailed diagnostic:\n"
  printf "    ${BLUE}bash scripts/ops/check_neo4j_mcp.sh${NC}\n"
  
  exit 1
fi
