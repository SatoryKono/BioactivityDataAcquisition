#!/bin/bash
# BioETL Docker setup and management script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
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

# Check Docker installation
check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker Desktop or Docker Engine."
        exit 1
    fi
    log_success "Docker found: $(docker --version)"
}

# Check Docker Compose
check_compose() {
    if ! command -v docker &> /dev/null || ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not available."
        exit 1
    fi
    log_success "Docker Compose found: $(docker compose version)"
}

# Build BioETL image
build_image() {
    log_info "Building BioETL image..."
    docker build -t bioetl:latest -f Dockerfile.bioetl . \
        --build-arg BUILDKIT_INLINE_CACHE=1 \
        --progress=plain
    log_success "BioETL image built successfully"
}

# Start services
start_services() {
    log_info "Starting Docker services..."
    
    # Start Neo4j for project-memory
    if [ "$1" == "full" ] || [ "$1" == "all" ]; then
        log_info "Starting Neo4j..."
        docker compose -f docker-compose.neo4j.yml up -d
        log_success "Neo4j started"
        
        # Start Redis
        log_info "Starting Redis..."
        docker compose -f scripts/ops/runtime/docker/compose/redis.yml up -d
        log_success "Redis started"
        
        # Start MinIO
        log_info "Starting MinIO..."
        docker compose -f scripts/ops/runtime/docker/compose/minio.yml up -d
        log_success "MinIO started"
        
        # Start Monitoring stack
        log_info "Starting monitoring stack..."
        docker compose -f docker-compose.monitoring.yml up -d
        log_success "Monitoring stack started"
    fi
    
    # Start main BioETL services
    log_info "Starting BioETL services..."
    docker compose up -d
    log_success "BioETL services started"
}

# Stop services
stop_services() {
    log_info "Stopping all services..."
    docker compose down
    
    if [ "$1" == "full" ] || [ "$1" == "all" ]; then
        docker compose -f docker-compose.neo4j.yml down || true
        docker compose -f scripts/ops/runtime/docker/compose/redis.yml down || true
        docker compose -f scripts/ops/runtime/docker/compose/minio.yml down || true
        docker compose -f docker-compose.monitoring.yml down || true
    fi
    
    log_success "Services stopped"
}

# View logs
view_logs() {
    local service=$1
    if [ -z "$service" ]; then
        docker compose logs -f
    else
        docker compose logs -f "$service"
    fi
}

# Health check
health_check() {
    log_info "Checking service health..."
    
    docker compose ps
    
    # Check BioETL health
    if docker compose exec -T bioetl curl -f http://127.0.0.1:8081/health/ready 2>/dev/null; then
        log_success "BioETL is healthy"
    else
        log_warning "BioETL health check failed"
    fi
}

# Clean up
cleanup() {
    log_warning "Removing Docker resources..."
    docker compose down --volumes
    docker rmi bioetl:latest || true
    log_success "Cleanup complete"
}

# Usage
usage() {
    cat << EOF
BioETL Docker Management Script

Usage: ./docker-setup.sh <command> [options]

Commands:
    check          Check Docker installation
    build          Build BioETL image
    start          Start main services
    start-full     Start all services (including Neo4j, Redis, monitoring)
    stop           Stop main services
    stop-full      Stop all services
    logs [service] View logs (optionally for specific service)
    health         Check service health
    clean          Remove all Docker resources
    help           Show this help message

Examples:
    ./docker-setup.sh check
    ./docker-setup.sh build
    ./docker-setup.sh start-full
    ./docker-setup.sh logs bioetl
    ./docker-setup.sh stop-full

EOF
}

# Main
main() {
    local command=$1
    
    case "$command" in
        check)
            check_docker
            check_compose
            ;;
        build)
            check_docker
            build_image
            ;;
        start)
            check_docker
            start_services
            health_check
            ;;
        start-full)
            check_docker
            build_image
            start_services "full"
            sleep 5
            health_check
            ;;
        stop)
            check_docker
            stop_services
            ;;
        stop-full)
            check_docker
            stop_services "full"
            ;;
        logs)
            check_docker
            view_logs "$2"
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
