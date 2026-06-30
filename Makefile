# BioETL local-first Makefile

.PHONY: help install test lint test-fast test-cov-fast-stable test-architecture test-unit test-integration test-ci-local test-profile test-deps run-local
.PHONY: docker-check docker-build docker-start docker-stop docker-logs docker-health docker-clean docker-compose-check
.PHONY: precommit-install qa-arch-fast quarantine-inspect quarantine-replay quarantine-purge release-lock

RUN ?= uv run
PIPELINE ?= chembl_activity
RUN_ID ?=
LOCAL_COV_FAIL_UNDER ?= 80

# Default target
help:
	@echo "BioETL Local-First Commands"
	@echo ""
	@echo "Local development:"
	@echo "  make install               Sync local development dependencies"
	@echo "  make test                  Run stable local tests with coverage"
	@echo "  make lint                  Run ruff and mypy checks"
	@echo "  make test-fast             Run fast non-slow tests"
	@echo "  make test-cov-fast-stable  Run fast coverage check"
	@echo "  make test-architecture     Run architecture tests"
	@echo "  make test-unit             Run unit tests"
	@echo "  make test-integration      Run non-e2e integration tests"
	@echo "  make test-ci-local         Run local CI-oriented test subset"
	@echo "  make test-profile          Run pytest duration profiling"
	@echo "  make test-deps             Verify test dependencies import"
	@echo "  make run-local             Run sample local pipeline"
	@echo ""
	@echo "Local governance:"
	@echo "  make precommit-install      Install local pre-commit hooks"
	@echo "  make qa-arch-fast           Run fast architecture checks"
	@echo ""
	@echo "Local operations:"
	@echo "  make quarantine-inspect     Inspect quarantine state for PIPELINE=$(PIPELINE)"
	@echo "  make quarantine-replay      Replay quarantine state for PIPELINE=$(PIPELINE)"
	@echo "  make quarantine-purge       Purge quarantine state for PIPELINE=$(PIPELINE)"
	@echo "  make release-lock           Release lock for PIPELINE=$(PIPELINE) RUN_ID=$(RUN_ID)"
	@echo ""
	@echo "Optional Docker helper commands:"
	@echo "  make docker-check           Check Docker installation"
	@echo "  make docker-build           Build BioETL image"
	@echo "  make docker-start           Start main services (bioetl + warp)"
	@echo "  make docker-start-full      Start all services (+ Neo4j, Redis, MinIO, monitoring)"
	@echo "  make docker-stop            Stop main services"
	@echo "  make docker-stop-full       Stop all services"
	@echo "  make docker-logs            View logs (all services)"
	@echo "  make docker-logs-bioetl     View BioETL logs only"
	@echo "  make docker-logs-warp       View Warp logs only"
	@echo "  make docker-health          Check service health"
	@echo "  make docker-clean           Remove containers, volumes, images"
	@echo "  make docker-compose-check   Validate docker-compose.yml"
	@echo "  make docker-shell-bioetl    Open shell in bioetl container"
	@echo "  make docker-shell-warp      Open shell in warp container"

install:
	uv sync --extra dev --extra tests --extra tests_full --extra export

test-deps:
	$(RUN) python -c "import pytest, pytest_cov, pytest_asyncio, hypothesis, vcr; print('test dependencies available')"

lint:
	$(RUN) ruff check src tests scripts
	$(RUN) mypy src/bioetl

test:
	$(RUN) pytest tests/ --ignore=tests/e2e --ignore=tests/contract --cov=src/bioetl --cov-fail-under=85

test-fast:
	$(RUN) pytest tests/ -q -m "not slow and not benchmark and not e2e and not memory" --ignore=tests/e2e

test-cov-fast-stable:
	$(RUN) pytest tests/unit tests/architecture -q --cov=src/bioetl --cov-fail-under=$(LOCAL_COV_FAIL_UNDER)

test-architecture:
	$(RUN) pytest tests/architecture/

test-unit:
	$(RUN) pytest tests/unit/

test-integration:
	$(RUN) pytest tests/integration/ -m "not e2e and not live"

test-ci-local:
	$(RUN) pytest tests/ -q --ignore=tests/e2e --ignore=tests/contract -m "not slow and not benchmark and not memory"

test-profile:
	$(RUN) pytest tests/ --durations=25 --durations-min=1.0 -q

run-local:
	$(RUN) bioetl run --pipeline $(PIPELINE) --limit 10

# Check Docker
docker-check:
	@echo "Checking Docker installation..."
	@docker --version
	@docker compose version
	@echo "✓ Docker is ready"

# Build BioETL image
docker-build: docker-check
	@echo "Building BioETL image..."
	docker build -t bioetl:latest -f Dockerfile.bioetl . \
		--build-arg BUILDKIT_INLINE_CACHE=1 \
		--progress=plain
	@echo "✓ BioETL image built"

# Start services (main only)
docker-start: docker-check
	@echo "Starting main services..."
	docker compose up -d
	@sleep 3
	@docker compose ps
	@echo "✓ Services started"

# Start full stack
docker-start-full: docker-check docker-build
	@echo "Starting full stack..."
	docker compose -f docker-compose.neo4j.yml up -d
	docker compose -f docker-compose.redis.yml up -d
	docker compose -f docker-compose.minio.yml up -d
	docker compose -f docker-compose.monitoring.yml up -d
	docker compose up -d
	@echo "Waiting for services to be ready..."
	@sleep 5
	@docker compose ps
	@echo "✓ Full stack started"

# Stop services (main only)
docker-stop: docker-check
	@echo "Stopping services..."
	docker compose down
	@echo "✓ Services stopped"

# Stop full stack
docker-stop-full: docker-check
	@echo "Stopping full stack..."
	docker compose down
	docker compose -f docker-compose.neo4j.yml down 2>/dev/null || true
	docker compose -f docker-compose.redis.yml down 2>/dev/null || true
	docker compose -f docker-compose.minio.yml down 2>/dev/null || true
	docker compose -f docker-compose.monitoring.yml down 2>/dev/null || true
	@echo "✓ Full stack stopped"

# View logs
docker-logs: docker-check
	docker compose logs -f

docker-logs-bioetl: docker-check
	docker compose logs -f bioetl

docker-logs-warp: docker-check
	docker compose logs -f warp

# Health check
docker-health: docker-check
	@echo "Checking service status..."
	@docker compose ps
	@echo ""
	@echo "Checking BioETL health..."
	@docker compose exec -T bioetl curl -f http://127.0.0.1:8081/health/ready 2>/dev/null && echo "✓ BioETL is healthy" || echo "⚠ BioETL health check failed"

# Validate compose files
docker-compose-check: docker-check
	@echo "Validating docker-compose.yml..."
	docker compose config > /dev/null
	@echo "✓ docker-compose.yml is valid"
	@echo ""
	@echo "Validating other compose files..."
	docker compose -f docker-compose.neo4j.yml config > /dev/null && echo "✓ neo4j valid" || true
	docker compose -f docker-compose.redis.yml config > /dev/null && echo "✓ redis valid" || true
	docker compose -f docker-compose.minio.yml config > /dev/null && echo "✓ minio valid" || true
	docker compose -f docker-compose.monitoring.yml config > /dev/null && echo "✓ monitoring valid" || true

# Shell access
docker-shell-bioetl: docker-check
	docker compose exec bioetl /bin/bash

docker-shell-warp: docker-check
	docker compose exec warp /bin/bash

# Clean up
docker-clean: docker-check
	@echo "Removing Docker resources..."
	docker compose down --volumes
	docker compose -f docker-compose.neo4j.yml down --volumes 2>/dev/null || true
	docker compose -f docker-compose.redis.yml down --volumes 2>/dev/null || true
	docker compose -f docker-compose.minio.yml down --volumes 2>/dev/null || true
	docker compose -f docker-compose.monitoring.yml down --volumes 2>/dev/null || true
	docker rmi bioetl:latest 2>/dev/null || true
	@echo "✓ Cleanup complete"

# Development shortcuts
docker-dev: docker-start
	@echo "Development environment ready"
	@echo "Available endpoints:"
	@echo "  BioETL:     http://localhost:8081"
	@echo "  Metrics:    http://localhost:8000"
	@echo "  Warp Proxy: http://localhost:9999"

# Local governance and live-ops shortcuts
precommit-install:
	bash scripts/ops/launchers/codex/setup_plugins.sh --hooks-only

qa-arch-fast:
	$(RUN) pytest tests/architecture/ -m "not slow and not serial and not memory"

quarantine-inspect:
	$(RUN) bioetl quarantine inspect --pipeline $(PIPELINE)

quarantine-replay:
	$(RUN) bioetl quarantine replay --pipeline $(PIPELINE)

quarantine-purge:
	$(RUN) bioetl quarantine purge --pipeline $(PIPELINE)

release-lock:
	$(RUN) bioetl lock release --pipeline $(PIPELINE) --run-id $(RUN_ID)

.PHONY: docker-dev
