#!/usr/bin/env bash
# Helper: Setup Mistral environment
# Configures Docker and creates docker-compose setup

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[!]${NC} $1"; }
log_error() { echo -e "${RED}[X]${NC} $1"; }
log_info() { echo -e "${BLUE}[i]${NC} $1"; }

echo ""
echo "=================================================="
echo "  Mistral Setup - Configuration"
echo "=================================================="
echo ""

# Step 1: Check Docker
log_info "STEP 1: Checking Docker..."
if ! command -v docker >/dev/null 2>&1; then
    log_error "Docker is not installed"
    log_info "Install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! docker ps >/dev/null 2>&1; then
    log_warn "Docker daemon not running"
    log_info "Please start Docker (or Docker Desktop on macOS/Windows)"
    exit 1
fi

log_success "Docker is ready: $(docker --version)"

# Step 2: Check Docker Compose
log_info "STEP 2: Checking Docker Compose..."
if ! docker compose version >/dev/null 2>&1; then
    log_error "Docker Compose not available"
    log_info "Install Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

log_success "Docker Compose ready"

echo ""

# Step 3: Create .env.mistrall
log_info "STEP 3: Creating .env.mistrall..."
ENV_FILE="${ROOT_DIR}/.env.mistrall"

if [[ -f "${ENV_FILE}" ]]; then
    log_success ".env.mistrall already exists"
else
    cat > "${ENV_FILE}" <<'EOF'
# Mistral Configuration
MISTRALL_PORT=11434
MISTRALL_MODEL=mistral:latest
MISTRALL_MEMORY=2g
DOCKER_BUILDKIT=1

# Ollama container name
OLLAMA_CONTAINER=mistral-ollama

# API endpoint
OLLAMA_API_URL=http://localhost:${MISTRALL_PORT}
EOF
    log_success ".env.mistrall created"
fi

# Step 4: Create docker-compose.mistrall.yml
log_info "STEP 4: Creating docker-compose.mistrall.yml..."
COMPOSE_FILE="${ROOT_DIR}/docker-compose.mistrall.yml"

if [[ -f "${COMPOSE_FILE}" ]]; then
    log_success "docker-compose.mistrall.yml already exists"
else
    cat > "${COMPOSE_FILE}" <<'EOF'
version: '3.9'

services:
  mistral-ollama:
    image: ollama/ollama:latest
    container_name: mistral-ollama
    restart: unless-stopped
    ports:
      - "${MISTRALL_PORT:-11434}:11434"
    environment:
      - OLLAMA_KEEP_ALIVE=24h
    volumes:
      - ollama-data:/root/.ollama
    entrypoint: ["ollama", "serve"]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11434/api/tags"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 30s

volumes:
  ollama-data:
    driver: local
EOF
    log_success "docker-compose.mistrall.yml created"
fi

echo ""

# Step 5: Pull Ollama image
log_info "STEP 5: Pulling Ollama image..."
if docker images | grep -q "ollama/ollama"; then
    log_success "Ollama image already present locally"
else
    log_info "Downloading ollama/ollama:latest (this may take a few minutes)..."
    if docker pull ollama/ollama:latest; then
        log_success "Ollama image pulled"
    else
        log_warn "Failed to pull Ollama image - will try again at startup"
    fi
fi

echo ""

# Step 6: Display next steps
echo "=================================================="
log_success "Setup completed successfully!"
echo "=================================================="
echo ""
log_info "Next steps:"
echo "  1. Start Mistral: ./run-mistrall.sh start"
echo "  2. Pull a model: ./run-mistrall.sh pull"
echo "  3. Check status: ./run-mistrall.sh status"
echo ""
log_info "API endpoint: http://localhost:${MISTRALL_PORT:-11434}"
echo ""

exit 0
