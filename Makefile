# BioETL local-first Makefile

.PHONY: help install test lint test-fast test-cov-fast-stable test-coverage test-architecture test-unit test-integration test-ci-local test-confidence-local test-confidence-unit test-confidence-contract test-profile test-deps run-local sync-windsurf-rules
.PHONY: docker-check docker-build docker-start docker-stop docker-logs docker-health docker-clean docker-compose-check
.PHONY: clean clean-all clean-local-artifacts clean-preflight precommit-install qa-arch-fast qa-debt security-check quarantine-inspect quarantine-replay quarantine-purge release-lock

RUN ?= uv run
PIPELINE ?= chembl_activity
RUN_ID ?=
LOCAL_COV_FAIL_UNDER ?= 80
QUALITY_EXEMPTIONS_REGISTRY ?= configs/quality/architecture_metric_exemptions.yaml
QUALITY_EXEMPTIONS_SCORECARD ?= configs/quality/debt_scorecard.yaml
QUALITY_REPORT_OUTPUT ?= reports/quality/ci-quality-metrics.json
QUALITY_SUMMARY_OUT ?=

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
	@echo "  make test-coverage         Run stable tests with canonical coverage gate"
	@echo "  make test-architecture     Run architecture tests"
	@echo "  make test-unit             Run unit tests"
	@echo "  make test-integration      Run non-e2e integration tests"
	@echo "  make security-check        Run security test suite"
	@echo "  make test-ci-local         Run local CI-oriented test subset"
	@echo "  make test-confidence-local Run pure unit, fast architecture, offline contracts, and 85% coverage"
	@echo "  make test-profile          Run pytest duration profiling"
	@echo "  make test-deps             Verify test dependencies import"
	@echo "  make run-local             Run sample local pipeline"
	@echo ""
	@echo "Local governance:"
	@echo "  make precommit-install      Install local pre-commit hooks"
	@echo "  make qa-debt                Run integral quality/debt gate"
	@echo "  make qa-arch-fast           Run fast architecture checks"
	@echo "  make sync-windsurf-rules    Sync Cursor rules to Windsurf/Cascade"
	@echo "  make clean                  Preview local cleanup targets"
	@echo "  make clean-local-artifacts  Apply local cleanup targets"
	@echo "  make clean-preflight        Run release-preflight cleanup"
	@echo ""
	@echo "Local operations:"
	@echo "  make quarantine-inspect     Inspect quarantine state for PIPELINE=$(PIPELINE)"
	@echo "  make quarantine-replay      Replay quarantine state for PIPELINE=$(PIPELINE)"
	@echo "  make quarantine-purge       Purge quarantine state for PIPELINE=$(PIPELINE)"
	@echo "  make release-lock           Release lock for PIPELINE=$(PIPELINE) RUN_ID=$(RUN_ID)"
	@echo ""
	@echo "Diagram tooling:"
	@echo "  make render-diagrams        Render SVG/PNG for all diagram sources"
	@echo "  make render-diagrams-svg    Render SVG only (faster local loop)"
	@echo "  make render-diagrams-checks Run PR-profile diagram validation"
	@echo "  make render-diagrams-bundles Regenerate Markdown diagram bundles"
	@echo "  make render-diagrams-all    Render artifacts and refresh bundles"
	@echo ""
	@echo "Optional Docker helper commands:"
	@echo "  make docker-check           Check Docker installation"
	@echo "  make docker-build           Build BioETL image"
	@echo "  make docker-start           Start the main BioETL adjunct"
	@echo "  make docker-start-full      Start helpers (+ Neo4j, Redis, MinIO; monitoring opt-in)"
	@echo "  make docker-start-monitoring  Opt-in Prometheus/Grafana/renderer only"
	@echo "  make docker-stop            Stop main services"
	@echo "  make docker-stop-full       Stop helper services"
	@echo "  make docker-stop-monitoring Stop opt-in monitoring stack"
	@echo "  make docker-logs            View logs (all services)"
	@echo "  make docker-logs-bioetl     View BioETL logs only"
	@echo "  make docker-health          Check service health"
	@echo "  make docker-clean           Stop containers; preserve volumes/images"
	@echo "  make docker-compose-check   Validate docker-compose.yml"
	@echo "  make docker-shell-bioetl    Open shell in bioetl container"

install:
	uv sync --extra dev --extra tests --extra tests_full --extra export

test-deps:
	$(RUN) python -c "import pytest, pytest_cov, pytest_asyncio, hypothesis, vcr; print('test dependencies available')"

lint:
	$(RUN) ruff check src tests scripts
	$(RUN) mypy src/bioetl

test:
	$(RUN) pytest tests/ --ignore=tests/e2e --ignore=tests/contract --cov=src/bioetl --cov-fail-under=85

test-coverage: test

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

test-confidence-unit:
	$(RUN) pytest tests/unit/ -q -m "not repo_backed and not slow and not serial and not benchmark and not memory"

test-confidence-contract:
	VCR_RECORD_MODE=none $(RUN) pytest tests/contract/ tests/unit/contracts/ -q -m "no_api or not network" -p no:xdist

test-confidence-local:
	$(MAKE) test-confidence-unit
	$(MAKE) qa-arch-fast
	$(MAKE) test-confidence-contract
	$(MAKE) test-coverage

test-profile:
	$(RUN) pytest tests/ --durations=25 --durations-min=1.0 -q

run-local:
	$(RUN) bioetl run --pipeline $(PIPELINE) --limit 10

# Check Docker
docker-check:
	bash scripts/ops/docker-setup.sh check main

# Build BioETL image
docker-build: docker-check
	@echo "Building BioETL image..."
	docker build -t bioetl:latest -f Dockerfile.bioetl . \
		--build-arg BUILDKIT_INLINE_CACHE=1 \
		--progress=plain
	@echo "✓ BioETL image built"

# Start services (main only)
docker-start: docker-check
	bash scripts/ops/docker-setup.sh start main

# Start full helper stack (monitoring is opt-in)
docker-start-full: docker-check docker-build
	bash scripts/ops/docker-setup.sh start-full

# Opt-in monitoring (Prometheus/Grafana/renderer only; no Loki/Tempo/Quarantine UI)
docker-start-monitoring: docker-check
	bash scripts/ops/docker-setup.sh monitoring

docker-stop-monitoring: docker-check
	bash scripts/ops/docker-setup.sh stop monitoring

# Stop services (main only)
docker-stop: docker-check
	bash scripts/ops/docker-setup.sh stop main

# Stop full helper stack (also stops monitoring if it was started)
docker-stop-full: docker-check
	bash scripts/ops/docker-setup.sh stop-full

# View logs
docker-logs: docker-check
	bash scripts/ops/docker-setup.sh logs main

docker-logs-bioetl: docker-check
	bash scripts/ops/docker-setup.sh logs main

# Health check
docker-health: docker-check
	bash scripts/ops/docker-setup.sh status main

# Validate compose files
docker-compose-check: docker-check
	@echo "Validating docker-compose.yml..."
	docker compose config > /dev/null
	@echo "✓ docker-compose.yml is valid"
	@echo ""
	@echo "Validating other compose files..."
	docker compose -f docker-compose.neo4j.yml config > /dev/null && echo "✓ neo4j valid" || true
	docker compose -f scripts/ops/runtime/docker/compose/redis.yml config > /dev/null && echo "✓ redis valid" || true
	docker compose -f scripts/ops/runtime/docker/compose/minio.yml config > /dev/null && echo "✓ minio valid" || true
	docker compose -f docker-compose.monitoring.yml config > /dev/null && echo "✓ monitoring valid" || true

# Shell access
docker-shell-bioetl: docker-check
	docker compose exec bioetl /bin/bash

# Clean up
docker-clean: docker-check
	$(RUN) python scripts/ops/runtime/docker/runtime_manager.py clean --stack main --confirm-destructive CLEAN

# Development shortcuts
docker-dev: docker-start
	@echo "Development environment ready"
	@echo "Available endpoints:"
	@echo "  BioETL:     http://localhost:8081"
	@echo "  Metrics:    http://localhost:8000"

# Local governance and live-ops shortcuts
sync-windsurf-rules:
	$(RUN) python scripts/ai/sync_windsurf_rules.py

precommit-install:
	bash scripts/ops/launchers/codex/setup_plugins.sh --hooks-only

clean:
	$(RUN) python -m scripts.engineering.diagnostics cleanup

clean-local-artifacts:
	$(RUN) python -m scripts.engineering.diagnostics cleanup $(if $(DRY_RUN),,--apply) $(if $(PURGE_LOGS),--purge-logs,)
	$(if $(PURGE_WORKTREES),$(RUN) python -m scripts.engineering.repo preflight-cleanup $(if $(DRY_RUN),--dry-run,),@true)

clean-preflight:
	$(RUN) python -m scripts.engineering.repo preflight-cleanup $(if $(DRY_RUN),--dry-run,)

clean-all:
	$(RUN) python -m scripts.engineering.diagnostics cleanup --apply --purge-logs
	$(RUN) python -m scripts.engineering.repo preflight-cleanup

qa-debt:
	$(RUN) python -m scripts.engineering.ci quality-gate \
		--registry "$(QUALITY_EXEMPTIONS_REGISTRY)" \
		--scorecard "$(QUALITY_EXEMPTIONS_SCORECARD)" \
		--output "$(QUALITY_REPORT_OUTPUT)" \
		--summary-out "$(QUALITY_SUMMARY_OUT)"

qa-arch-fast:
	BIOETL_PYTEST_SHARDED_TEST_HEALTH_SUITE=architecture-fast-boundary bash scripts/engineering/dev/run_pytest_sharded.sh --shard S7-architecture-fast-boundary --stream -- tests/architecture/ -m "architecture and not slow and not benchmark and not memory"

security-check:
	$(RUN) pytest tests/security/ -q

quarantine-inspect:
	$(RUN) bioetl quarantine inspect --pipeline $(PIPELINE)

quarantine-replay:
	$(RUN) bioetl quarantine replay --pipeline $(PIPELINE)

quarantine-purge:
	$(RUN) bioetl quarantine purge --pipeline $(PIPELINE)

release-lock:
	$(RUN) bioetl lock release --pipeline $(PIPELINE) --run-id $(RUN_ID)

.PHONY: render-diagrams render-diagrams-svg render-diagrams-checks render-diagrams-bundles render-diagrams-all

render-diagrams:
	bash docs/02-architecture/diagrams/tooling/render.sh

render-diagrams-svg:
	bash docs/02-architecture/diagrams/tooling/render.sh --svg-only

render-diagrams-checks:
	bash scripts/diagrams/run_diagram_checks.sh --profile pr

render-diagrams-bundles:
	$(RUN) python scripts/diagrams/generate_all_bundles.py

render-diagrams-all: render-diagrams render-diagrams-bundles

.PHONY: docker-dev
