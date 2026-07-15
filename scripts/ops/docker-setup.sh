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
DOCKER_PREFLIGHT="scripts/ops/runtime/docker/docker_runtime_preflight.py"
DOCKER_CONTRACT="configs/quality/docker_runtime_contracts.yaml"
MAIN_PROJECT="bioetl-main"
MAIN_COMPOSE="docker-compose.yml"
MONITORING_PROJECT="bioetl-monitoring"
MONITORING_COMPOSE="docker-compose.monitoring.yml"
MONITORING_SERVICES=(prometheus pushgateway renderer grafana)
declare -A RESTART_BASELINE=()

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

require_env_file() {
    if [[ -f .env ]]; then
        return 0
    fi

    log_error ".env file is missing."
    log_warning "Guardrail: Docker helper never creates or edits .env files."
    log_warning "Provide the required values through an existing approved .env or process environment, then retry."
    exit 2
}

python_command() {
    if [[ -n "${BIOETL_PYTHON:-}" ]] && command -v "$BIOETL_PYTHON" >/dev/null 2>&1; then
        printf '%s\n' "$BIOETL_PYTHON"
        return 0
    fi
    command -v python >/dev/null 2>&1 && printf '%s\n' "python" && return 0
    command -v python3 >/dev/null 2>&1 && printf '%s\n' "python3" && return 0
    log_error "Python is required for the Docker runtime preflight."
    return 1
}

run_runtime_preflight() {
    local phase="$1"
    local python_bin
    local report="reports/quality/docker-runtime-${phase}.json"
    python_bin="$(python_command)"
    log_info "Running fail-closed Docker runtime ${phase} preflight..."
    if ! BIOETL_REPO_ROOT="$PROJECT_ROOT" "$python_bin" "$DOCKER_PREFLIGHT" \
        --contract "$DOCKER_CONTRACT" --output "$report"; then
        log_error "Docker runtime ${phase} preflight failed. Review $report before mutation."
        return 1
    fi
    "$python_bin" -c 'import json, pathlib, sys
payload = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
for row in payload.get("live", {}).get("compose_projects", []):
    name = str(row.get("Name") or row.get("name") or "")
    raw = row.get("ConfigFiles") or row.get("ConfigFile") or []
    files = raw if isinstance(raw, list) else [item.strip() for item in str(raw).split(",") if item.strip()]
    normalized = [str(item).replace("\\", "/") for item in files]
    if any(item.startswith("/tmp/") for item in normalized):
        raise SystemExit(f"{name}: /tmp Compose config origin is forbidden")
    if name.startswith("bioetl-") and len(normalized) != 1:
        raise SystemExit(f"{name}: multiple owning Compose files are forbidden: {normalized}")' "$report"
    log_success "Docker runtime ${phase} preflight passed."
}

restart_key() { printf '%s/%s\n' "$1" "$3"; }

capture_restart_baseline() {
    local project="$1" compose_file="$2"
    shift 2
    local service container_id count key
    for service in "$@"; do
        key="$(restart_key "$project" "$compose_file" "$service")"
        container_id="$(docker compose -p "$project" -f "$compose_file" ps -q "$service" 2>/dev/null)"
        count=0
        if [[ -n "$container_id" ]]; then
            count="$(docker inspect --format '{{.RestartCount}}' "$container_id")"
        fi
        RESTART_BASELINE["$key"]="$count"
    done
}

verify_service_state() {
    local project="$1" compose_file="$2" service="$3"
    local container_id state oom health restarts baseline key
    key="$(restart_key "$project" "$compose_file" "$service")"
    container_id="$(docker compose -p "$project" -f "$compose_file" ps -q "$service")"
    [[ -n "$container_id" ]] || { log_error "$project/$service has no owned container."; return 1; }
    read -r state oom health restarts < <(
        docker inspect --format '{{.State.Status}} {{.State.OOMKilled}} {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}} {{.RestartCount}}' "$container_id"
    )
    baseline="${RESTART_BASELINE[$key]:-0}"
    [[ "$state" == "running" && "$oom" == "false" ]] || { log_error "$project/$service failed state/OOM verification: state=$state oom=$oom"; return 1; }
    [[ "$health" == "none" || "$health" == "healthy" ]] || { log_error "$project/$service is not healthy: $health"; return 1; }
    (( restarts <= baseline )) || { log_error "$project/$service restart count increased: $baseline -> $restarts"; return 1; }
}

wait_for_backend_readiness() {
    local python_bin
    python_bin="$(python_command)"
    "$python_bin" -c 'import json, time, urllib.request
url = "http://127.0.0.1:8081/ops/control-plane/ready"
deadline = time.monotonic() + 90
while time.monotonic() < deadline:
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            payload = json.load(response)
        if response.status < 400 and isinstance(payload, dict): raise SystemExit(0)
    except Exception: time.sleep(1)
raise SystemExit("BioETL control-plane readiness timed out")'
}

verify_prometheus_runtime_identity() {
    local python_bin host_start container_payload container_start
    python_bin="$(python_command)"
    host_start="$("$python_bin" -c 'import json,sys,urllib.request; print(json.load(urllib.request.urlopen(sys.argv[1], timeout=5))["data"]["startTime"])' "http://127.0.0.1:9090/api/v1/status/runtimeinfo")"
    container_payload="$(docker compose -p "$MONITORING_PROJECT" -f "$MONITORING_COMPOSE" exec -T prometheus wget -qO- http://127.0.0.1:9090/api/v1/status/runtimeinfo)"
    container_start="$(printf '%s' "$container_payload" | "$python_bin" -c 'import json,sys; print(json.load(sys.stdin)["data"]["startTime"])')"
    [[ -n "$host_start" && "$host_start" == "$container_start" ]] || { log_error "Host and container-network Prometheus runtime identities differ."; return 1; }
    log_success "Prometheus runtime identity converged."
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
    require_env_file
    run_runtime_preflight "pre"
    ensure_external_networks
    capture_restart_baseline "$MAIN_PROJECT" "$MAIN_COMPOSE" bioetl
    log_info "Starting the explicit BioETL backend service..."
    docker compose -p "$MAIN_PROJECT" -f "$MAIN_COMPOSE" up -d --wait --wait-timeout 120 bioetl
    wait_for_backend_readiness
    verify_service_state "$MAIN_PROJECT" "$MAIN_COMPOSE" bioetl
    run_runtime_preflight "post"
    log_success "BioETL backend is ready and postflight passed."
}

start_full_stack() {
    require_env_file
    run_runtime_preflight "pre"
    ensure_external_networks
    capture_restart_baseline "$MAIN_PROJECT" "$MAIN_COMPOSE" bioetl
    capture_restart_baseline "$MONITORING_PROJECT" "$MONITORING_COMPOSE" "${MONITORING_SERVICES[@]}"
    log_info "Starting the explicit BioETL backend service..."
    docker compose -p "$MAIN_PROJECT" -f "$MAIN_COMPOSE" up -d --wait --wait-timeout 120 bioetl
    wait_for_backend_readiness
    verify_service_state "$MAIN_PROJECT" "$MAIN_COMPOSE" bioetl

    log_info "Starting Neo4j..."
    docker compose -p bioetl-neo4j -f docker-compose.neo4j.yml up -d neo4j
    log_success "Neo4j started."

    log_info "Starting Redis..."
    docker compose -p bioetl-redis -f scripts/ops/runtime/docker/compose/redis.yml up -d redis redis-exporter
    log_success "Redis started."

    log_info "Starting MinIO..."
    docker compose -p bioetl-minio -f scripts/ops/runtime/docker/compose/minio.yml up -d minio
    log_success "MinIO started."

    log_info "Starting monitoring stack..."
    docker compose -p "$MONITORING_PROJECT" -f "$MONITORING_COMPOSE" up -d --wait --wait-timeout 120 "${MONITORING_SERVICES[@]}"
    for service in "${MONITORING_SERVICES[@]}"; do verify_service_state "$MONITORING_PROJECT" "$MONITORING_COMPOSE" "$service"; done
    verify_prometheus_runtime_identity
    run_runtime_preflight "post"
    log_success "Full helper stack is ready and postflight passed."
}

start_monitoring() {
    require_env_file
    run_runtime_preflight "pre"
    ensure_external_networks
    wait_for_backend_readiness || { log_error "Monitoring requires the canonical bioetl-main HTTP backend on 127.0.0.1:8081."; return 1; }
    capture_restart_baseline "$MONITORING_PROJECT" "$MONITORING_COMPOSE" "${MONITORING_SERVICES[@]}"
    log_info "Starting monitoring stack..."
    docker compose -p "$MONITORING_PROJECT" -f "$MONITORING_COMPOSE" up -d --wait --wait-timeout 120 "${MONITORING_SERVICES[@]}"
    for service in "${MONITORING_SERVICES[@]}"; do verify_service_state "$MONITORING_PROJECT" "$MONITORING_COMPOSE" "$service"; done
    verify_prometheus_runtime_identity
    run_runtime_preflight "post"
    log_success "Monitoring stack is ready and postflight passed."
}

start_mcp() {
    require_env_file
    run_runtime_preflight "pre"
    ensure_external_networks
    log_info "Starting MCP servers..."
    docker compose -p bioetl-codex -f docker-compose.codex.yml up -d
    log_success "MCP servers started."
}

stop_main_stack() {
    log_info "Stopping BioETL services..."
    docker compose -p bioetl-main -f docker-compose.yml down
    log_success "BioETL services stopped."
}

stop_full_stack() {
    log_info "Stopping all Docker helper services..."
    docker compose -p bioetl-main -f docker-compose.yml down
    docker compose -p bioetl-neo4j -f docker-compose.neo4j.yml down
    docker compose -p bioetl-redis -f scripts/ops/runtime/docker/compose/redis.yml down
    docker compose -p bioetl-minio -f scripts/ops/runtime/docker/compose/minio.yml down
    docker compose -p bioetl-monitoring -f docker-compose.monitoring.yml down
    docker compose -p bioetl-codex -f docker-compose.codex.yml down
    log_success "All Docker helper services stopped."
}

view_logs() {
    local service="${1:-}"
    if [[ -z "$service" ]]; then
        docker compose -p bioetl-main -f docker-compose.yml logs -f
    else
        docker compose -p bioetl-main -f docker-compose.yml logs -f "$service"
    fi
}

health_check() {
    log_info "Checking service health..."
    docker compose -p bioetl-main -f docker-compose.yml ps

    if docker compose -p bioetl-main -f docker-compose.yml exec -T bioetl curl -f http://127.0.0.1:8081/health/ready 2>/dev/null; then
        log_success "BioETL is healthy."
    else
        log_warning "BioETL health check failed."
        return 1
    fi
}

cleanup() {
    log_warning "Removing Docker resources for the main BioETL stack."
    docker compose -p bioetl-main -f docker-compose.yml down --volumes
    if docker image inspect bioetl:latest >/dev/null 2>&1; then docker rmi bioetl:latest; fi
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
    if (( $# > 0 )); then shift; fi

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
            ;;
        start-full|full)
            check_docker
            build_image
            start_full_stack
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
