#!/usr/bin/env bash
# Quick start script: Launch Neo4j backend and verify MCP
# Usage: bash scripts/ops/runtime/neo4j/neo4j_quick_start.sh

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../../.." && pwd)"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# Check prerequisites
section "Prerequisites Check"

if ! command -v docker >/dev/null 2>&1; then
  fail "Docker not found. Please install Docker first."
  exit 1
fi
ok "Docker is installed"

if ! command -v codex >/dev/null 2>&1; then
  warn "Codex CLI not found in PATH. Some features will be unavailable."
fi

: "${NEO4J_USERNAME:?NEO4J_USERNAME is required}"
: "${NEO4J_PASSWORD:?NEO4J_PASSWORD is required}"

section "Docker Compose Owner"

if ! docker network inspect bioetl-runtime >/dev/null 2>&1; then
  fail "External network bioetl-runtime is missing. Run scripts/ops/docker-setup.sh first."
  exit 1
fi

info "Starting the single owner: docker compose -p bioetl-neo4j"
if ! docker compose \
  -p bioetl-neo4j \
  -f "${REPO_ROOT}/docker-compose.neo4j.yml" \
  up -d --wait --wait-timeout 240; then
  fail "Neo4j Compose project did not become ready within 240 seconds"
  docker compose -p bioetl-neo4j -f "${REPO_ROOT}/docker-compose.neo4j.yml" logs --tail 50 neo4j >&2
  exit 1
fi
ok "Neo4j Compose project is healthy"

# Verify port accessibility
section "Port Verification"

info "Checking Bolt port (7687)..."
if command -v nc >/dev/null 2>&1; then
  if nc -z localhost 7687 2>/dev/null; then
    ok "Port 7687 is open and listening"
  else
    warn "Port 7687 not yet responding (container may still be starting)"
  fi
elif timeout 2 bash -c "echo >/dev/tcp/localhost/7687" 2>/dev/null; then
  ok "Port 7687 is open and listening"
else
  warn "Could not verify port 7687 (checking skipped)"
fi

# Check MCP registration (if Codex available)
if command -v codex >/dev/null 2>&1; then
  section "MCP Registration"

  if codex mcp list 2>/dev/null | grep -q "neo4j-memory"; then
    ok "neo4j-memory MCP server is registered"

    config=$(codex mcp get neo4j-memory 2>/dev/null || echo "")
    if grep -q "mcp_neo4j_memory_wrapper" <<<"$config"; then
      ok "neo4j-memory uses correct wrapper script"
    fi
  else
    warn "neo4j-memory not registered in Codex"
    info "Run: uv run python -m scripts.engineering.dev setup-mcp"
  fi
else
  info "Codex not available, skipping MCP check"
fi

# Final summary
section "Summary"

info "Neo4j Backend Status:"
printf "  ${BLUE}Container:${NC} bioetl-neo4j\n"
printf "  ${BLUE}HTTP UI:${NC}   http://localhost:7474/browser/\n"
printf "  ${BLUE}Bolt:${NC}      bolt://localhost:7687\n"
printf "  ${BLUE}Auth:${NC}      supplied via NEO4J_USERNAME / NEO4J_PASSWORD\n"

printf "\n${GREEN}Next steps:${NC}\n"
printf "  1. Access Neo4j Browser at http://localhost:7474/browser/\n"
printf "  2. Run verification: ${BLUE}bash scripts/ai/mcp/check_neo4j_memory.sh${NC}\n"
printf "  3. Use in Codex: ${BLUE}codex interactive${NC}\n"
printf "  4. Stop project: ${BLUE}docker compose -p bioetl-neo4j -f docker-compose.neo4j.yml down${NC}\n"

ok "Setup complete!"
exit 0
