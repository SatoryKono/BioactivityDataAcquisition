#!/usr/bin/env bash
# Helper: Check Mistral environment (Docker + Ollama)
# Called by: run-mistrall.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[⚠]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1" >&2; }
log_info() { echo -e "${BLUE}[i]${NC} $1"; }

echo ""
echo "=================================================="
echo "  Mistral Environment Check"
echo "=================================================="
echo ""

ALL_CHECKS=true

# 1. Check Docker
log_info "Checking Docker..."
if command -v docker >/dev/null 2>&1; then
    DOCKER_VER=$(docker --version)
    log_success "Docker installed: $DOCKER_VER"
else
    log_warn "Docker not found"
    ALL_CHECKS=false
fi

# 2. Check Docker daemon
log_info "Checking Docker daemon..."
if docker ps >/dev/null 2>&1; then
    log_success "Docker daemon running"
else
    log_warn "Docker daemon not accessible - may need to start Docker"
    ALL_CHECKS=false
fi

# 3. Check Docker Compose
log_info "Checking Docker Compose..."
if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    COMPOSE_VER=$(docker compose version)
    log_success "Docker Compose available: $COMPOSE_VER"
else
    log_warn "Docker Compose not available"
    ALL_CHECKS=false
fi

# 4. Check .env.mistrall
log_info "Checking configuration..."
ENV_FILE="${ROOT_DIR}/.env.mistrall"
if [[ -f "${ENV_FILE}" ]]; then
    log_success ".env.mistrall exists"
else
    log_warn ".env.mistrall not found"
    ALL_CHECKS=false
fi

# 5. Check docker-compose.mistrall.yml
log_info "Checking docker-compose.mistrall.yml..."
COMPOSE_FILE="${ROOT_DIR}/docker-compose.mistrall.yml"
if [[ -f "${COMPOSE_FILE}" ]]; then
    log_success "docker-compose.mistrall.yml exists"
else
    log_warn "docker-compose.mistrall.yml not found"
    ALL_CHECKS=false
fi

# 6. Check Ollama image
log_info "Checking Ollama image..."
if docker images | grep -q "ollama"; then
    log_success "Ollama image found locally"
else
    log_warn "Ollama image not found - will pull on startup"
fi

echo ""

# Return exit code
if [[ "${ALL_CHECKS}" == "true" ]]; then
    log_success "All checks passed"
    exit 0
else
    log_warn "Some checks failed - will attempt to fix"
    exit 1
fi
