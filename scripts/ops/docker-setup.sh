#!/bin/bash
# Canonical optional Docker helper entrypoint for BioETL.
#
# This script retains the legacy root docker-setup.sh command verbs from the
# retired root helper while keeping maintained logic under scripts/ops/**.
# Docker remains an optional local-only adjunct; it is not the ADR-010 runtime
# bootstrap path.

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_docker() {
    if ! command -v docker >/dev/null 2>&1; then
        log_error "Docker is not installed. Please install Docker Desktop or Docker Engine."
        exit 1
    fi

    if ! docker ps >/dev/null 2>&1; then
        log_error "Docker is not running or is not accessible."
        exit 1
    fi

    log_success "Docker found: $(docker --version)"
}

check_compose() {
    if ! docker compose version >/dev/null 2>&1; then
        log_error "Docker Compose is not available."
        exit 1
    fi

    log_success "Docker Compose found: $(docker compose version)"
}

ensure_env_file() {
    if [[ -f .env ]]; then
        return 0
    fi

    if [[ "${BIOETL_CREATE_LOCAL_ENV_FILES:-}" == "1" ]]; then
        if [[ ! -f .env.example ]]; then
            log_error ".env.example not found; .env was not created."
            exit 2
        fi
        log_warning ".env file is missing; BIOETL_CREATE_LOCAL_ENV_FILES=1 allows creating it from the example."
        cp .env.example .env
        log_success "Created .env file. Edit it before using secrets."
        return 0
    fi

    log_error ".env file is missing."
    log_warning "Guardrail: Docker helper не создает .env автоматически."
    log_warning "Create it manually after an explicit local decision: cp .env.example .env"
    log_warning "Rerun with BIOETL_CREATE_LOCAL_ENV_FILES=1 only when local .env creation is intended."
    log_warning "Default behavior is non-mutating without BIOETL_CREATE_LOCAL_ENV_FILES=1."
    exit 2
}

ensure_external_network() {
    local network_name="$1"

    if docker network inspect "$network_name" >/dev/null 2>&1; then
        log_success "Docker network ready: $network_name"
        return 0
    fi

    log_info "Creating shared Docker network: $network_name"
    docker network create "$network_name" >/dev/null
    log_success "Docker network ready: $network_name"
}

ensure_external_networks() {
    ensure_external_network "bioetl-monitoring"
    ensure_external_network "warp-network"
}

build_image() {
    log_info "Building BioETL image..."
    docker build -t bioetl:latest -f Dockerfile.bioetl . \
        --build-arg BUILDKIT_INLINE_CACHE=1 \
        --progress=plain
    log_success "BioETL image built successfully."
}

start_main_stack() {
    ensure_env_file
    ensure_external_networks
    log_info "Starting BioETL services..."
    docker compose up -d
    log_success "BioETL services started."
}

start_full_stack() {
    ensure_env_file
    ensure_external_networks

    log_info "Starting Neo4j..."
    docker compose -f docker-compose.neo4j.yml up -d
    log_success "Neo4j started."

    log_info "Starting Redis..."
    docker compose -f scripts/ops/runtime/docker/compose/redis.yml up -d
    log_success "Redis started."

    log_info "Starting MinIO..."
    docker compose -f scripts/ops/runtime/docker/compose/minio.yml up -d
    log_success "MinIO started."

    log_info "Starting monitoring stack..."
    docker compose -f docker-compose.monitoring.yml up -d
    log_success "Monitoring stack started."

    log_info "Starting BioETL services..."
    docker compose up -d
    log_success "BioETL services started."
}

start_monitoring() {
    ensure_env_file
    ensure_external_networks
    log_info "Starting monitoring stack..."
    docker compose -f docker-compose.monitoring.yml up -d
    log_success "Monitoring stack started."
}

start_mcp() {
    ensure_env_file
    ensure_external_networks
    log_info "Starting MCP servers..."
    docker compose -f docker-compose.codex.yml up -d
    log_success "MCP servers started."
}

stop_main_stack() {
    log_info "Stopping BioETL services..."
    docker compose down
    log_success "BioETL services stopped."
}

stop_full_stack() {
    log_info "Stopping all Docker helper services..."
    docker compose down
    docker compose -f docker-compose.neo4j.yml down || true
    docker compose -f scripts/ops/runtime/docker/compose/redis.yml down || true
    docker compose -f scripts/ops/runtime/docker/compose/minio.yml down || true
    docker compose -f docker-compose.monitoring.yml down || true
    docker compose -f docker-compose.codex.yml down || true
    log_success "All Docker helper services stopped."
}

view_logs() {
    local service="${1:-}"
    if [[ -z "$service" ]]; then
        docker compose logs -f
    else
        docker compose logs -f "$service"
    fi
}

health_check() {
    log_info "Checking service health..."
    docker compose ps

    if docker compose exec -T bioetl curl -f http://127.0.0.1:8081/health/ready 2>/dev/null; then
        log_success "BioETL is healthy."
    else
        log_warning "BioETL health check failed."
    fi
}

cleanup() {
    log_warning "Removing Docker resources for the main BioETL stack."
    docker compose down --volumes
    docker rmi bioetl:latest || true
    log_success "Cleanup complete."
}

usage() {
    cat <<'EOF'
BioETL Docker Management Script

Usage: scripts/ops/docker-setup.sh <command> [options]

Commands:
    check          Check Docker and Docker Compose availability
    build          Build bioetl:latest from Dockerfile.bioetl
    start          Start main services and check health
    start-full     Build the image, start full helper stack, and check health
    stop           Stop main services
    stop-full      Stop main plus helper compose stacks
    logs [service] View logs, optionally for a specific service
    health         Check service health
    clean          Remove main stack volumes and bioetl:latest image
    basic          Alias for start
    full           Alias for start-full
    monitoring     Start monitoring stack only
    mcp            Start Codex MCP stack only
    help           Show this help message

Examples:
    scripts/ops/docker-setup.sh check
    scripts/ops/docker-setup.sh build
    scripts/ops/docker-setup.sh start-full
    scripts/ops/docker-setup.sh logs bioetl
    scripts/ops/docker-setup.sh stop-full
EOF
}

main() {
    local command="${1:-help}"
    shift || true

    case "$command" in
        check)
            check_docker
            check_compose
            ;;
        build)
            check_docker
            build_image
            ;;
        start|basic)
            check_docker
            start_main_stack
            sleep 2
            health_check
            ;;
        start-full|full)
            check_docker
            build_image
            start_full_stack
            sleep 5
            health_check
            ;;
        monitoring)
            check_docker
            start_monitoring
            ;;
        mcp)
            check_docker
            start_mcp
            ;;
        stop)
            check_docker
            stop_main_stack
            ;;
        stop-full)
            check_docker
            stop_full_stack
            ;;
        logs)
            check_docker
            view_logs "${1:-}"
            ;;
        health)
            check_docker
            health_check
            ;;
        clean)
            check_docker
            cleanup
            ;;
        help|--help|-h|"")
            usage
            ;;
        *)
            log_error "Unknown command: $command"
            usage
            exit 1
            ;;
    esac
}

main "$@"
