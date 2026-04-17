#!/usr/bin/env bash
# Quick start script: Launch Neo4j backend and verify MCP
# Usage: bash scripts/ops/neo4j_quick_start.sh

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

ok() { printf "${GREEN}[✓]${NC} %s\n" "$1"; }
warn() { printf "${YELLOW}[⚠]${NC} %s\n" "$1"; }
fail() { printf "${RED}[✗]${NC} %s\n" "$1" >&2; }
info() { printf "${BLUE}[i]${NC} %s\n" "$1"; }
section() { printf "\n${BLUE}=== %s ===${NC}\n" "$1"; }

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

# Check if container already exists
section "Docker Container Status"

if docker ps -a --format "table {{.Names}}" | grep -q "^bioetl-neo4j$"; then
  if docker ps --format "table {{.Names}}" | grep -q "^bioetl-neo4j$"; then
    ok "Container bioetl-neo4j is already RUNNING"
    docker ps | grep bioetl-neo4j | sed 's/^/  /'
  else
    warn "Container bioetl-neo4j exists but is STOPPED"
    info "Starting container..."
    docker start bioetl-neo4j
    sleep 5
    ok "Container started"
  fi
else
  section "Starting Neo4j Container"
  
  info "Launching: docker run -d --name bioetl-neo4j -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/bioetl_secure_password neo4j:5.15-community"
  
  if docker run -d --name bioetl-neo4j \
    -p 7474:7474 -p 7687:7687 \
    -e NEO4J_AUTH=neo4j/bioetl_secure_password \
    neo4j:5.15-community >/dev/null 2>&1; then
    ok "Container created successfully"
    
    info "Waiting for Neo4j to start (this takes ~10-15 seconds)..."
    sleep 3
    
    # Wait for Bolt port to be ready
    max_attempts=30
    attempt=0
    while [[ $attempt -lt $max_attempts ]]; do
      if docker logs bioetl-neo4j 2>/dev/null | grep -q "Started"; then
        ok "Neo4j started successfully"
        break
      fi
      
      if docker logs bioetl-neo4j 2>/dev/null | grep -q "ERROR"; then
        fail "Neo4j startup error detected"
        docker logs bioetl-neo4j | grep ERROR >&2
        exit 1
      fi
      
      sleep 1
      attempt=$((attempt + 1))
    done
    
    if [[ $attempt -ge $max_attempts ]]; then
      warn "Timeout waiting for Neo4j to start, continuing anyway..."
    fi
  else
    fail "Failed to create container"
    exit 1
  fi
fi

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
    info "Run: uv run python -m scripts.dev setup-mcp"
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
printf "  ${BLUE}Username:${NC}  neo4j\n"
printf "  ${BLUE}Password:${NC}  bioetl_secure_password\n"

printf "\n${GREEN}Next steps:${NC}\n"
printf "  1. Access Neo4j Browser at http://localhost:7474/browser/\n"
printf "  2. Run verification: ${BLUE}bash scripts/ai/mcp/check_neo4j_memory.sh${NC}\n"
printf "  3. Use in Codex: ${BLUE}codex interactive${NC}\n"
printf "  4. Stop container: ${BLUE}docker stop bioetl-neo4j${NC}\n"
printf "  5. Remove container: ${BLUE}docker rm bioetl-neo4j${NC}\n"

ok "Setup complete!"
exit 0
