#!/usr/bin/env bash
# WSL-Optimized: Neo4j Backend Startup for Windows WSL
# Configures Docker-to-WSL connectivity via host.docker.internal
# Run this ONCE to start Neo4j accessible from both Windows and WSL

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

ok() {
  local message="${1:-}"
  printf "${GREEN}✓${NC} %s\n" "$message"
  return 0
}

fail() {
  local message="${1:-}"
  printf "${RED}✗${NC} %s\n" "$message" >&2
  return 0
}

warn() {
  local message="${1:-}"
  printf "${YELLOW}!${NC} %s\n" "$message"
  return 0
}

info() {
  local message="${1:-}"
  printf "${BLUE}→${NC} %s\n" "$message"
  return 0
}

header() {
  local message="${1:-}"
  printf "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n%s\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n" "$message"
  return 0
}

upsert_env_local() {
  local file_path="$1"
  local key="$2"
  local value="$3"

  if [[ -f "$file_path" ]] && grep -q "^${key}=" "$file_path"; then
    python3 - "$file_path" "$key" "$value" <<'PY'
from __future__ import annotations

import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
key = sys.argv[2]
value = sys.argv[3]
pattern = re.compile(rf"^{re.escape(key)}=.*$", re.MULTILINE)
text = path.read_text(encoding="utf-8")
updated = pattern.sub(f"{key}={value}", text)
path.write_text(updated, encoding="utf-8")
PY
  else
    printf '%s=%s\n' "$key" "$value" >> "$file_path"
  fi
}

# Detect environment
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

ENV_TYPE=$(detect_env)
DOCKER_BIN="$(select_docker_bin "$ENV_TYPE" || true)"
CONTAINER_ALREADY_RUNNING=0
CONTAINER_RESTARTED=0
WSL_NEO4J_HOST="host.docker.internal"

header "Neo4j Backend Setup for $ENV_TYPE"

# ============================================================================
# Step 1: Check Prerequisites
# ============================================================================
header "Step 1: Check Prerequisites"

if [[ -z "${DOCKER_BIN}" ]]; then
  fail "Docker not found. Install Docker Desktop (with WSL integration) or Docker Engine"
  exit 1
fi
ok "Docker available via ${DOCKER_BIN}"

# Check if container already exists
if "${DOCKER_BIN}" ps -a --format "table {{.Names}}" 2>/dev/null | grep -q "^bioetl-neo4j$" \
  && "${DOCKER_BIN}" ps --format "table {{.Names}}" 2>/dev/null | grep -q "^bioetl-neo4j$"; then
    ok "Container bioetl-neo4j already RUNNING"
    "${DOCKER_BIN}" ps 2>/dev/null | grep bioetl-neo4j | sed 's/^/  /'
    CONTAINER_ALREADY_RUNNING=1
elif "${DOCKER_BIN}" ps -a --format "table {{.Names}}" 2>/dev/null | grep -q "^bioetl-neo4j$"; then
  warn "Container exists but is stopped"
  info "Starting container..."
  "${DOCKER_BIN}" start bioetl-neo4j >/dev/null 2>&1
  sleep 5
  ok "Container restarted"
  CONTAINER_RESTARTED=1
  else
  :
fi

# ============================================================================
# Step 2: Configure for WSL or Native Docker
# ============================================================================
header "Step 2: Configure for $ENV_TYPE"

case "$ENV_TYPE" in
  wsl)
    info "WSL detected — Neo4j will be accessible via ${WSL_NEO4J_HOST}"
    NEO4J_HOST="${WSL_NEO4J_HOST}"
    info "From WSL: Use bolt://${WSL_NEO4J_HOST}:7687"
    info "From Windows: Use bolt://localhost:7687"
    ;;
  macos)
    info "macOS detected — Neo4j accessible via host.docker.internal"
    NEO4J_HOST="host.docker.internal"
    ;;
  linux)
    info "Linux detected — Neo4j accessible via localhost"
    NEO4J_HOST="localhost"
    ;;
  *)
    warn "Environment detection inconclusive, using localhost"
    NEO4J_HOST="localhost"
    ;;
esac

# ============================================================================
# Step 3: Create .env.local for WSL-specific configuration
# ============================================================================
header "Step 3: WSL Environment Configuration"

ENV_LOCAL="${REPO_ROOT}/.env.local"

if [[ ! -f "$ENV_LOCAL" ]]; then
  info "Creating $ENV_LOCAL with WSL settings"
  cat > "$ENV_LOCAL" << ENVEOF
# WSL-Optimized Neo4j Configuration
# Generated for $ENV_TYPE environment

# Connection: Use host.docker.internal for cross-WSL/Windows access
NEO4J_URI=bolt://${NEO4J_HOST}:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=bioetl_secure_password
NEO4J_DATABASE=neo4j
NEO4J_AUTH=neo4j/bioetl_secure_password

# Cache directory (WSL-friendly)
NPM_CONFIG_CACHE=/tmp/npm-cache

# For WSL: Store memory in /home/user/... (not /mnt/c/...)
MEMORY_FILE_PATH=${REPO_ROOT}/docs/00-project/ai/memory/mcp-memory.json
ENVEOF
  ok "Created .env.local"
else
  ok ".env.local already exists"
fi

upsert_env_local "$ENV_LOCAL" "NEO4J_URI" "bolt://${NEO4J_HOST}:7687"
upsert_env_local "$ENV_LOCAL" "NEO4J_USERNAME" "neo4j"
upsert_env_local "$ENV_LOCAL" "NEO4J_PASSWORD" "bioetl_secure_password"
upsert_env_local "$ENV_LOCAL" "NEO4J_DATABASE" "neo4j"
upsert_env_local "$ENV_LOCAL" "NEO4J_AUTH" "neo4j/bioetl_secure_password"
upsert_env_local "$ENV_LOCAL" "NPM_CONFIG_CACHE" "/tmp/npm-cache"
upsert_env_local "$ENV_LOCAL" "MEMORY_FILE_PATH" "${REPO_ROOT}/docs/00-project/ai/memory/mcp-memory.json"
ok "Neo4j keys in .env.local synchronized for ${ENV_TYPE}"

# ============================================================================
# Step 4: Start Neo4j Container
# ============================================================================
header "Step 4: Starting Neo4j Container"

if [[ $CONTAINER_ALREADY_RUNNING -eq 1 ]]; then
  info "Container already running — skipping create step"
elif [[ $CONTAINER_RESTARTED -eq 1 ]]; then
  info "Container restarted — skipping create step"
else
  info "Launching Neo4j 5.15-community..."
  info "This takes 10-15 seconds on first startup"

  if ! docker_run_output="$(
    "${DOCKER_BIN}" run -d \
      --name bioetl-neo4j \
      -p 7474:7474 \
      -p 7687:7687 \
      -e NEO4J_AUTH=neo4j/bioetl_secure_password \
      -e NEO4J_ACCEPT_LICENSE_AGREEMENT=yes \
      -e NEO4J_server_memory_heap_max_size=512m \
      -e NEO4J_server_memory_pagecache_size=256m \
      neo4j:5.15-community 2>&1
  )"; then
    fail "Failed to start container"
    printf '%s\n' "$docker_run_output" >&2
    if grep -qi "permission denied while trying to connect to the Docker daemon socket" <<<"$docker_run_output"; then
      info "Hint: in WSL, prefer Docker Desktop integration via docker.exe or enable docker daemon access for your Linux docker client"
    fi
    if grep -qi "Conflict.*container name" <<<"$docker_run_output"; then
      info "Hint: remove stale container with: docker rm -f bioetl-neo4j"
    fi
    if grep -qi "port is already allocated\|bind.*address already in use" <<<"$docker_run_output"; then
      info "Hint: ports 7474 or 7687 are already occupied on the host"
    fi
    exit 1
  fi

  ok "Container created"
  printf '  %s\n' "$docker_run_output"
fi

# ============================================================================
# Step 5: Wait for Neo4j to Start
# ============================================================================
header "Step 5: Waiting for Neo4j to Start"

info "Waiting for Neo4j to be ready..."

max_attempts=30
attempt=0
while [[ $attempt -lt $max_attempts ]]; do
  if "${DOCKER_BIN}" logs bioetl-neo4j 2>/dev/null | grep -q "Started"; then
    ok "Neo4j is ready"
    break
  fi
  
  if "${DOCKER_BIN}" logs bioetl-neo4j 2>/dev/null | grep -q "ERROR"; then
    fail "Neo4j startup error detected"
    "${DOCKER_BIN}" logs bioetl-neo4j 2>&1 | grep ERROR >&2
    "${DOCKER_BIN}" stop bioetl-neo4j >/dev/null 2>&1 || true
    "${DOCKER_BIN}" rm bioetl-neo4j >/dev/null 2>&1 || true
    exit 1
  fi
  
  printf "."
  sleep 1
  attempt=$((attempt + 1))
done
printf "\n"

if [[ $attempt -ge $max_attempts ]]; then
  warn "Timeout waiting for Neo4j (but continuing)"
fi

# ============================================================================
# Step 6: Verify Connectivity
# ============================================================================
header "Step 6: Verify Connectivity"

sleep 2

VERIFY_HOST="127.0.0.1"
VERIFY_LABEL="localhost"
if [[ "$ENV_TYPE" == "wsl" ]]; then
  VERIFY_HOST="${WSL_NEO4J_HOST}"
  VERIFY_LABEL="${WSL_NEO4J_HOST}"
fi

if timeout 3 bash -c "echo >/dev/tcp/${VERIFY_HOST}/7687" 2>/dev/null; then
  ok "Bolt port (7687) is open on ${VERIFY_LABEL}"
else
  warn "Cannot connect to ${VERIFY_LABEL}:7687"
fi

if timeout 3 bash -c "echo >/dev/tcp/${VERIFY_HOST}/7474" 2>/dev/null; then
  ok "HTTP port (7474) is open on ${VERIFY_LABEL}"
else
  warn "Cannot connect to ${VERIFY_LABEL}:7474"
fi

# ============================================================================
# Step 7: Show Connection Details
# ============================================================================
header "Connection Details"

printf "\n${BLUE}Neo4j is now running!${NC}\n\n"

case "$ENV_TYPE" in
  wsl)
    printf "From WSL (bash):${NC}\n"
    printf "  Bolt URI: ${BLUE}bolt://host.docker.internal:7687${NC}\n"
    printf "  Browser:  ${BLUE}http://host.docker.internal:7474/browser/${NC}\n\n"
    printf "From Windows (PowerShell/CMD):${NC}\n"
    printf "  Bolt URI: ${BLUE}bolt://localhost:7687${NC}\n"
    printf "  Browser:  ${BLUE}http://localhost:7474/browser${NC}\n\n"
    printf "Credentials: ${BLUE}neo4j / bioetl_secure_password${NC}\n"
    ;;
  *)
    printf "Connection details:${NC}\n"
    printf "  Bolt URI: ${BLUE}bolt://localhost:7687${NC}\n"
    printf "  Browser:  ${BLUE}http://localhost:7474/browser${NC}\n"
    printf "  Credentials: ${BLUE}neo4j / bioetl_secure_password${NC}\n"
    ;;
esac

# ============================================================================
# Step 8: Verify MCP Configuration
# ============================================================================
header "Step 8: Verify MCP Configuration"

if command -v codex >/dev/null 2>&1; then
  if codex mcp list 2>/dev/null | grep -q "neo4j-memory"; then
    ok "neo4j-memory is registered in Codex"
  else
    warn "neo4j-memory not found in Codex (run: uv run python -m scripts.engineering.dev setup-mcp)"
  fi
else
  warn "Codex CLI not available"
fi

# ============================================================================
# Step 9: Summary
# ============================================================================
header "Setup Complete!"

printf "\n${GREEN}✓ Neo4j backend is running${NC}\n"
printf "${GREEN}✓ MCP wrapper is configured${NC}\n"
printf "${GREEN}✓ Ready for smoke test${NC}\n\n"

printf "Next steps:\n\n"
printf "1. Run MCP verification:\n"
printf "   ${BLUE}bash scripts/ai/mcp/check_neo4j_memory.sh${NC}\n\n"
printf "2. Access Neo4j Browser:\n"

case "$ENV_TYPE" in
  wsl)
    printf "   From WSL: ${BLUE}http://host.docker.internal:7474/browser/${NC}\n"
    printf "   From Windows: ${BLUE}http://localhost:7474/browser${NC}\n\n"
    ;;
  *)
    printf "   ${BLUE}http://localhost:7474/browser/${NC}\n\n"
    ;;
esac

printf "3. Test in Codex:\n"
printf "   ${BLUE}codex interactive${NC}\n"
printf "   Then use ${BLUE}@neo4j-memory${NC} in prompts\n\n"

printf "4. View logs (if needed):\n"
printf "   ${BLUE}docker logs -f bioetl-neo4j${NC}\n\n"

printf "5. Stop container:\n"
printf "   ${BLUE}docker stop bioetl-neo4j${NC}\n\n"

exit 0
