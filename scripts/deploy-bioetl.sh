#!/usr/bin/env bash
# ==============================================================================
# BioETL Docker Compose Deployment Script
#
# Usage: ./scripts/deploy-bioetl.sh [action] [environment]
#
# Actions:
#   deploy       - Build and start all services (app + infra + monitoring)
#   start        - Start existing containers (no rebuild)
#   stop         - Stop all services (preserve data)
#   restart      - Restart all services
#   update       - Rebuild and restart the BioETL app container
#   teardown     - Stop services and remove volumes (destructive)
#   status       - Show service status and health
#   logs         - Stream logs from services
#   shell        - Open a shell in the BioETL container
#   run-pipeline - Run a pipeline inside the container
#   backup       - Backup data volumes to local archive
#   restore      - Restore data volumes from archive
#
# Environments: dev (default), staging, prod
#
# BioETL v6.0.0 | ADR-010: Local-Only Deployment
# ==============================================================================

set -euo pipefail

# ------------------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

ACTION="${1:-help}"
ENV="${2:-dev}"
COMPONENT="${3:-}"

# Compose files
COMPOSE_INFRA="$REPO_ROOT/docker-compose.yml"
COMPOSE_APP="$REPO_ROOT/docker-compose.app.yml"
COMPOSE_MONITORING="$REPO_ROOT/docker-compose.monitoring.yml"

# Backup directory
BACKUP_DIR="$REPO_ROOT/backups"

# Colors
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[0;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m'

# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------
info()    { echo -e "${BLUE}[info]${NC} $*"; }
success() { echo -e "${GREEN}[ok]${NC} $*"; }
warn()    { echo -e "${YELLOW}[warn]${NC} $*"; }
error()   { echo -e "${RED}[error]${NC} $*" >&2; }

# Build the -f flags for docker compose based on what's requested
compose_cmd() {
    local files=()
    files+=(-f "$COMPOSE_INFRA")
    files+=(-f "$COMPOSE_APP")
    echo "${files[@]}"
}

compose_all() {
    local files=()
    files+=(-f "$COMPOSE_INFRA")
    files+=(-f "$COMPOSE_APP")
    files+=(-f "$COMPOSE_MONITORING")
    echo "${files[@]}"
}

check_prerequisites() {
    local missing=0

    if ! command -v docker &>/dev/null; then
        error "docker is not installed. Install Docker: https://docs.docker.com/get-docker/"
        missing=1
    fi

    if ! docker compose version &>/dev/null 2>&1; then
        error "docker compose plugin is not available."
        error "Install it: https://docs.docker.com/compose/install/"
        missing=1
    fi

    if [[ ! -f "$COMPOSE_INFRA" ]]; then
        error "Missing $COMPOSE_INFRA"
        missing=1
    fi

    if [[ ! -f "$COMPOSE_APP" ]]; then
        error "Missing $COMPOSE_APP"
        missing=1
    fi

    if [[ $missing -ne 0 ]]; then
        exit 1
    fi
}

ensure_env_file() {
    if [[ ! -f "$REPO_ROOT/.env" ]]; then
        if [[ -f "$REPO_ROOT/.env.example" ]]; then
            warn ".env file not found. Copying from .env.example..."
            cp "$REPO_ROOT/.env.example" "$REPO_ROOT/.env"
            warn "Edit .env to set your API keys and secrets before production use."
        else
            error ".env file not found and no .env.example available."
            exit 1
        fi
    fi
}

# ------------------------------------------------------------------------------
# Actions
# ------------------------------------------------------------------------------
do_deploy() {
    info "Deploying BioETL ($ENV environment)..."
    check_prerequisites
    ensure_env_file

    export BIOETL_ENV="$ENV"

    # Build images
    info "Building images..."
    # shellcheck disable=SC2046
    docker compose $(compose_all) build

    # Start services
    info "Starting services..."
    # shellcheck disable=SC2046
    docker compose $(compose_all) up -d

    # Wait for health checks
    info "Waiting for services to become healthy..."
    local retries=30
    local count=0
    while [[ $count -lt $retries ]]; do
        if docker inspect --format='{{.State.Health.Status}}' bioetl-app 2>/dev/null | grep -q "healthy"; then
            break
        fi
        count=$((count + 1))
        sleep 2
    done

    if [[ $count -ge $retries ]]; then
        warn "BioETL container did not reach healthy state within 60s."
        warn "Check logs: ./scripts/deploy-bioetl.sh logs bioetl"
    else
        success "BioETL container is healthy."
    fi

    echo ""
    success "Deployment complete!"
    echo ""
    info "Access points:"
    echo "  - BioETL metrics : http://localhost:${BIOETL_METRICS_PORT:-8000}/metrics"
    echo "  - Neo4j browser  : http://localhost:${NEO4J_HTTP_PORT:-7474}"
    echo "  - Prometheus     : http://localhost:9090"
    echo "  - Grafana        : http://localhost:3000"
    echo ""
    info "Quick commands:"
    echo "  ./scripts/deploy-bioetl.sh status"
    echo "  ./scripts/deploy-bioetl.sh logs bioetl"
    echo "  ./scripts/deploy-bioetl.sh run-pipeline chembl_activity --limit 10"
}

do_start() {
    info "Starting existing BioETL services..."
    check_prerequisites
    ensure_env_file

    export BIOETL_ENV="$ENV"

    # shellcheck disable=SC2046
    docker compose $(compose_all) start
    success "Services started."
}

do_stop() {
    info "Stopping BioETL services (data preserved)..."
    # shellcheck disable=SC2046
    docker compose $(compose_all) stop
    success "Services stopped. Data volumes preserved."
}

do_restart() {
    info "Restarting BioETL services..."
    export BIOETL_ENV="$ENV"

    # shellcheck disable=SC2046
    docker compose $(compose_all) restart
    success "Services restarted."
}

do_update() {
    info "Rebuilding and restarting BioETL application..."
    check_prerequisites
    ensure_env_file

    export BIOETL_ENV="$ENV"

    # Rebuild only the app service
    # shellcheck disable=SC2046
    docker compose $(compose_cmd) build bioetl

    # Recreate only the app container (zero-downtime for infra services)
    # shellcheck disable=SC2046
    docker compose $(compose_cmd) up -d --no-deps bioetl

    success "BioETL application updated."
}

do_teardown() {
    warn "This will stop all services and DELETE all data volumes."
    echo -n "Are you sure? (yes/no): "
    read -r reply
    if [[ "$reply" == "yes" ]]; then
        # shellcheck disable=SC2046
        docker compose $(compose_all) down -v --remove-orphans
        success "All services stopped and volumes removed."
    else
        info "Cancelled."
    fi
}

do_status() {
    info "BioETL Service Status ($ENV)"
    echo "--------------------------------------------"

    echo ""
    info "Containers:"
    # shellcheck disable=SC2046
    docker compose $(compose_all) ps 2>/dev/null || true

    echo ""
    info "Container health:"
    for name in bioetl-app bioetl-neo4j bioetl-prometheus bioetl-grafana cloudflare-warp; do
        local state
        state=$(docker inspect --format='{{.State.Status}}' "$name" 2>/dev/null || echo "not found")
        local health
        health=$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}no healthcheck{{end}}' "$name" 2>/dev/null || echo "-")
        printf "  %-22s status=%-10s health=%s\n" "$name" "$state" "$health"
    done

    echo ""
    info "Volumes:"
    docker volume ls --filter name=bioactivitydataacquisition 2>/dev/null || true

    echo ""
    info "Disk usage:"
    docker system df 2>/dev/null || true

    echo ""
    info "Network:"
    # shellcheck disable=SC2046
    docker compose $(compose_all) port bioetl 8000 2>/dev/null && true
}

do_logs() {
    local target="${COMPONENT:-}"
    local extra_args=("${@:4}")

    if [[ -z "$target" ]]; then
        # All services
        # shellcheck disable=SC2046
        docker compose $(compose_all) logs -f --tail=100
    elif [[ "$target" == "bioetl" ]]; then
        docker logs -f --tail=100 bioetl-app
    elif [[ "$target" == "neo4j" ]]; then
        docker logs -f --tail=100 bioetl-neo4j
    elif [[ "$target" == "prometheus" ]]; then
        docker logs -f --tail=100 bioetl-prometheus
    elif [[ "$target" == "grafana" ]]; then
        docker logs -f --tail=100 bioetl-grafana
    else
        # Try as container name directly
        docker logs -f --tail=100 "$target"
    fi
}

do_shell() {
    info "Opening shell in BioETL container..."
    docker exec -it bioetl-app /bin/bash
}

do_run_pipeline() {
    local pipeline="${COMPONENT:-}"
    if [[ -z "$pipeline" ]]; then
        error "Usage: ./scripts/deploy-bioetl.sh run-pipeline <pipeline_name> [options]"
        error "Example: ./scripts/deploy-bioetl.sh run-pipeline chembl_activity --limit 10"
        exit 1
    fi
    shift 2  # Remove action and env
    shift    # Remove pipeline name (already captured in COMPONENT)
    info "Running pipeline: $pipeline $*"
    docker exec bioetl-app bioetl run --pipeline "$pipeline" "$@"
}

do_backup() {
    local timestamp
    timestamp=$(date +%Y%m%d_%H%M%S)
    local archive="$BACKUP_DIR/bioetl-backup-${ENV}-${timestamp}.tar.gz"

    mkdir -p "$BACKUP_DIR"
    info "Creating backup: $archive"

    # Stop app to ensure data consistency
    info "Stopping BioETL app for consistent backup..."
    docker stop bioetl-app 2>/dev/null || true

    # Copy data from volume
    docker run --rm \
        -v bioactivitydataacquisition_bioetl-data:/data:ro \
        -v "$BACKUP_DIR":/backup \
        alpine:3.19 \
        tar czf "/backup/bioetl-backup-${ENV}-${timestamp}.tar.gz" -C /data .

    # Restart app
    docker start bioetl-app 2>/dev/null || true

    success "Backup created: $archive"
    ls -lh "$archive"
}

do_restore() {
    local archive="${COMPONENT:-}"
    if [[ -z "$archive" ]]; then
        error "Usage: ./scripts/deploy-bioetl.sh restore <env> <archive_path>"
        error "Available backups:"
        ls -1 "$BACKUP_DIR"/bioetl-backup-*.tar.gz 2>/dev/null || echo "  (no backups found)"
        exit 1
    fi

    if [[ ! -f "$archive" ]]; then
        error "Archive not found: $archive"
        exit 1
    fi

    warn "This will overwrite current data with backup: $archive"
    echo -n "Are you sure? (yes/no): "
    read -r reply
    if [[ "$reply" != "yes" ]]; then
        info "Cancelled."
        return
    fi

    info "Stopping BioETL app..."
    docker stop bioetl-app 2>/dev/null || true

    info "Restoring from: $archive"
    docker run --rm \
        -v bioactivitydataacquisition_bioetl-data:/data \
        -v "$(cd "$(dirname "$archive")" && pwd)":/backup:ro \
        alpine:3.19 \
        sh -c "rm -rf /data/* && tar xzf /backup/$(basename "$archive") -C /data"

    docker start bioetl-app 2>/dev/null || true
    success "Data restored from $archive"
}

show_help() {
    cat << 'EOF'
BioETL Docker Compose Deployment Script

Usage: ./scripts/deploy-bioetl.sh <action> [environment] [args...]

Actions:
  deploy         Build and start all services (app + infra + monitoring)
  start          Start existing containers (no rebuild)
  stop           Stop all services (preserve data volumes)
  restart        Restart all services
  update         Rebuild and restart only the BioETL app container
  teardown       Stop services and remove ALL volumes (destructive!)
  status         Show service status, health, and disk usage
  logs [svc]     Stream logs (services: bioetl, neo4j, prometheus, grafana)
  shell          Open bash shell in the BioETL container
  run-pipeline   Run a pipeline inside the container
  backup         Backup data volume to local archive
  restore        Restore data volume from archive

Environments:
  dev            Development (default)
  staging        Staging
  prod           Production

Examples:
  ./scripts/deploy-bioetl.sh deploy dev
  ./scripts/deploy-bioetl.sh status
  ./scripts/deploy-bioetl.sh logs bioetl
  ./scripts/deploy-bioetl.sh update prod
  ./scripts/deploy-bioetl.sh run-pipeline dev chembl_activity --limit 10
  ./scripts/deploy-bioetl.sh backup prod
  ./scripts/deploy-bioetl.sh restore prod backups/bioetl-backup-prod-20260225.tar.gz
  ./scripts/deploy-bioetl.sh teardown dev

Configuration:
  Environment variables are loaded from .env (copied from .env.example).
  See .env.example for all available settings.

Architecture:
  This script uses Docker Compose (ADR-010: Local-Only Deployment).
  Compose files:
    docker-compose.yml             Infrastructure (Cloudflare WARP + Neo4j)
    docker-compose.app.yml         BioETL application
    docker-compose.monitoring.yml  Prometheus + Grafana monitoring stack
EOF
}

# ------------------------------------------------------------------------------
# Main
# ------------------------------------------------------------------------------
cd "$REPO_ROOT"

case "$ACTION" in
    deploy)       do_deploy ;;
    start)        do_start ;;
    stop)         do_stop ;;
    restart)      do_restart ;;
    update)       do_update ;;
    teardown)     do_teardown ;;
    status)       do_status ;;
    logs)         do_logs "$@" ;;
    shell)        do_shell ;;
    run-pipeline) do_run_pipeline "$@" ;;
    backup)       do_backup ;;
    restore)      do_restore ;;
    help|--help|-h)
                  show_help ;;
    *)
        error "Unknown action: $ACTION"
        echo ""
        show_help
        exit 1
        ;;
esac
