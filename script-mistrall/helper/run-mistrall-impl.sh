#!/usr/bin/env bash
# Helper: Run Mistral operations (start, stop, logs, etc.)
# Called by: run-mistrall.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="${REPO_ROOT:-.}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_success() {
    local message="${1:-}"
    echo -e "${GREEN}[✓]${NC} ${message}"
    return 0
}

log_warn() {
    local message="${1:-}"
    echo -e "${YELLOW}[⚠]${NC} ${message}"
    return 0
}

log_error() {
    local message="${1:-}"
    echo -e "${RED}[✗]${NC} ${message}" >&2
    return 0
}

log_info() {
    local message="${1:-}"
    echo -e "${BLUE}[i]${NC} ${message}"
    return 0
}

# Load environment
ENV_FILE="${ROOT_DIR}/.env.mistrall"
if [[ -f "${ENV_FILE}" ]]; then
    set -a
    source "${ENV_FILE}"
    set +a
fi

MISTRALL_PORT="${MISTRALL_PORT:-11434}"
MISTRALL_MODEL="${MISTRALL_MODEL:-mistral:latest}"
OLLAMA_CONTAINER="${OLLAMA_CONTAINER:-mistral-ollama}"
COMPOSE_FILE="${ROOT_DIR}/docker-compose.mistrall.yml"
CONTAINER_PATTERN="${OLLAMA_CONTAINER}"

# Function: Start service
start_service() {
    log_info "Starting Mistral Ollama service..."
    
    cd "${ROOT_DIR}"
    
    if docker compose -f "${COMPOSE_FILE}" up; then
        log_success "Mistral started on port ${MISTRALL_PORT}"
    else
        log_error "Failed to start Mistral"
        return 1
    fi
    return 0
}

# Function: Start daemon
start_daemon() {
    log_info "Starting Mistral as daemon..."
    
    cd "${ROOT_DIR}"
    
    if docker compose -f "${COMPOSE_FILE}" up -d; then
        log_success "Mistral daemon started (container: ${OLLAMA_CONTAINER})"
        log_info "API: http://localhost:${MISTRALL_PORT}"
        log_info "View logs: ./run-mistrall.sh logs"
    else
        log_error "Failed to start daemon"
        return 1
    fi
    return 0
}

# Function: Stop service
stop_service() {
    log_info "Stopping Mistral..."
    
    cd "${ROOT_DIR}"
    
    if docker compose -f "${COMPOSE_FILE}" down; then
        log_success "Mistral stopped"
    else
        log_warn "Container already stopped or not found"
    fi
    return 0
}

# Function: Show status
show_status() {
    log_info "Checking Mistral status..."
    
    if docker ps -a | grep -q "${CONTAINER_PATTERN}"; then
        if docker ps | grep -q "${CONTAINER_PATTERN}"; then
            log_success "Mistral container is RUNNING"
            docker ps --filter "name=${OLLAMA_CONTAINER}" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
            
            # Check API health
            if curl -s http://localhost:${MISTRALL_PORT}/api/tags >/dev/null 2>&1; then
                log_success "API is responding"
                log_info "Endpoint: http://localhost:${MISTRALL_PORT}"
            else
                log_warn "API not responding yet (container may be starting)"
            fi
        else
            log_warn "Mistral container exists but is NOT running"
            docker ps -a --filter "name=${OLLAMA_CONTAINER}" --format "table {{.Names}}\t{{.Status}}"
        fi
    else
        log_warn "Mistral container not found"
        log_info "Start with: ./run-mistrall.sh daemon"
    fi
    return 0
}

# Function: Show logs
show_logs() {
    log_info "Showing Mistral logs..."
    
    cd "${ROOT_DIR}"
    docker compose -f "${COMPOSE_FILE}" logs -f
    return 0
}

# Function: Shell access
shell_access() {
    log_info "Opening shell in Mistral container..."
    
    CONTAINER_ID=$(docker ps -q -f "name=${OLLAMA_CONTAINER}" | head -1)
    
    if [[ -z "${CONTAINER_ID}" ]]; then
        log_error "Mistral container not running"
        exit 1
    fi
    
    docker exec -it "${CONTAINER_ID}" bash || true
    return 0
}

# Function: Pull model
pull_model() {
    log_info "Pulling model: ${MISTRALL_MODEL}"
    
    CONTAINER_ID=$(docker ps -q -f "name=${OLLAMA_CONTAINER}" | head -1)
    
    if [[ -z "${CONTAINER_ID}" ]]; then
        log_error "Mistral container not running"
        log_info "Start it first: ./run-mistrall.sh daemon"
        return 1
    fi
    
    if docker exec -it "${CONTAINER_ID}" ollama pull "${MISTRALL_MODEL}"; then
        log_success "Model pulled: ${MISTRALL_MODEL}"
    else
        log_error "Failed to pull model"
        return 1
    fi
    return 0
}

# Main dispatcher
COMMAND="${1:-start}"
shift || true

case "$COMMAND" in
    start)
        start_service
        ;;
    
    daemon)
        start_daemon
        ;;
    
    stop)
        stop_service
        ;;
    
    status)
        show_status
        ;;
    
    logs)
        show_logs
        ;;
    
    shell)
        shell_access
        ;;
    
    pull)
        pull_model
        ;;
    
    *)
        log_error "Unknown operation: $COMMAND"
        exit 1
        ;;
esac

exit $?
