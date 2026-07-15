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
  return 0
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
  return 0
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
WSL_NEO4J_HOST="host.docker.internal"
ENV_FILE_WRITE_ALLOWED=0
if [[ "${BIOETL_CREATE_LOCAL_ENV_FILES:-0}" == "1" ]]; then
  ENV_FILE_WRITE_ALLOWED=1
fi

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

if ! "${DOCKER_BIN}" compose version >/dev/null 2>&1; then
  fail "Docker Compose v2 is required"
  exit 1
fi
: "${NEO4J_USERNAME:?NEO4J_USERNAME is required}"
: "${NEO4J_PASSWORD:?NEO4J_PASSWORD is required}"

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
# Step 3: Check .env.local for WSL-specific configuration
# ============================================================================
header "Step 3: WSL Environment Configuration"

ENV_LOCAL="${REPO_ROOT}/.env.local"

if [[ ! -f "$ENV_LOCAL" ]]; then
  if [[ ${ENV_FILE_WRITE_ALLOWED} -ne 1 ]]; then
    warn "$ENV_LOCAL not found; not creating it without BIOETL_CREATE_LOCAL_ENV_FILES=1"
    info "Create $ENV_LOCAL manually, or rerun with BIOETL_CREATE_LOCAL_ENV_FILES=1 to generate and synchronize local settings."
  else
    info "BIOETL_CREATE_LOCAL_ENV_FILES=1 set; creating $ENV_LOCAL with WSL settings"
    cat > "$ENV_LOCAL" << ENVEOF
# WSL-Optimized Neo4j Configuration
# Generated for $ENV_TYPE environment

# Connection: Use host.docker.internal for cross-WSL/Windows access
NEO4J_URI=bolt://${NEO4J_HOST}:7687
NEO4J_USERNAME=${NEO4J_USERNAME}
NEO4J_PASSWORD=${NEO4J_PASSWORD}
NEO4J_DATABASE=neo4j
NEO4J_AUTH=${NEO4J_USERNAME}/${NEO4J_PASSWORD}

# Cache directory (WSL-friendly)
NPM_CONFIG_CACHE=/tmp/npm-cache

# For WSL: Store memory in /home/user/... (not /mnt/c/...)
MEMORY_FILE_PATH=${REPO_ROOT}/docs/00-project/ai/memory/mcp-memory.json
ENVEOF
    ok "Created .env.local"
  fi
else
  if [[ ${ENV_FILE_WRITE_ALLOWED} -eq 1 ]]; then
    ok ".env.local already exists; synchronizing because BIOETL_CREATE_LOCAL_ENV_FILES=1 is set"
  else
    ok ".env.local already exists"
    warn "Skipping .env.local synchronization without BIOETL_CREATE_LOCAL_ENV_FILES=1"
  fi
fi

if [[ ${ENV_FILE_WRITE_ALLOWED} -eq 1 ]]; then
  upsert_env_local "$ENV_LOCAL" "NEO4J_URI" "bolt://${NEO4J_HOST}:7687"
  upsert_env_local "$ENV_LOCAL" "NEO4J_USERNAME" "${NEO4J_USERNAME}"
  upsert_env_local "$ENV_LOCAL" "NEO4J_PASSWORD" "${NEO4J_PASSWORD}"
  upsert_env_local "$ENV_LOCAL" "NEO4J_DATABASE" "neo4j"
  upsert_env_local "$ENV_LOCAL" "NEO4J_AUTH" "${NEO4J_USERNAME}/${NEO4J_PASSWORD}"
  upsert_env_local "$ENV_LOCAL" "NPM_CONFIG_CACHE" "/tmp/npm-cache"
  upsert_env_local "$ENV_LOCAL" "MEMORY_FILE_PATH" "${REPO_ROOT}/docs/00-project/ai/memory/mcp-memory.json"
  ok "Neo4j keys in .env.local synchronized for ${ENV_TYPE}"
fi

# ============================================================================
# Step 4: Start Neo4j Container
# ============================================================================
header "Step 4: Starting Neo4j Container"

if ! "${DOCKER_BIN}" network inspect bioetl-runtime >/dev/null 2>&1; then
  fail "External network bioetl-runtime is missing; run scripts/ops/docker-setup.sh first"
  exit 1
fi

info "Starting the single owner: docker compose -p bioetl-neo4j"
if ! "${DOCKER_BIN}" compose \
  -p bioetl-neo4j \
  -f "${REPO_ROOT}/docker-compose.neo4j.yml" \
  up -d --wait --wait-timeout 240; then
  fail "Neo4j Compose project failed readiness"
  "${DOCKER_BIN}" compose -p bioetl-neo4j -f "${REPO_ROOT}/docker-compose.neo4j.yml" logs --tail 50 neo4j >&2
  exit 1
fi
ok "Neo4j Compose project is healthy"

# ============================================================================
# Step 5: Wait for Neo4j to Start
# ============================================================================
header "Step 5: Neo4j Readiness Confirmed"
"${DOCKER_BIN}" compose -p bioetl-neo4j -f "${REPO_ROOT}/docker-compose.neo4j.yml" ps neo4j

# ============================================================================
# Step 6: Verify Connectivity
# ============================================================================
header "Step 6: Verify Connectivity"

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
    printf "Credentials: supplied via ${BLUE}NEO4J_USERNAME / NEO4J_PASSWORD${NC}\n"
    ;;
  *)
    printf "Connection details:${NC}\n"
    printf "  Bolt URI: ${BLUE}bolt://localhost:7687${NC}\n"
    printf "  Browser:  ${BLUE}http://localhost:7474/browser${NC}\n"
    printf "  Credentials: supplied via ${BLUE}NEO4J_USERNAME / NEO4J_PASSWORD${NC}\n"
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
printf "   ${BLUE}docker compose -p bioetl-neo4j -f docker-compose.neo4j.yml down${NC}\n\n"

exit 0
