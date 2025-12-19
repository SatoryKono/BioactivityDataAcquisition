# BioETL Makefile
# Production-ready ETL system for bioactivity data

.PHONY: help install test lint run-local docker-up docker-down docker-reset seed-local clean
.DEFAULT_GOAL := help

# Python
PYTHON := python
VENV := .venv
VENV_BIN := $(VENV)/Scripts
ifeq ($(OS),Windows_NT)
	VENV_PYTHON := $(VENV_BIN)/python.exe
	VENV_PIP := $(VENV_BIN)/pip.exe
else
	VENV_BIN := $(VENV)/bin
	VENV_PYTHON := $(VENV_BIN)/python
	VENV_PIP := $(VENV_BIN)/pip
endif

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)BioETL - Available Commands:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

install: ## Create venv and install dependencies
	@echo "$(BLUE)Creating virtual environment...$(NC)"
	$(PYTHON) -m venv $(VENV)
	@echo "$(BLUE)Upgrading pip...$(NC)"
	$(VENV_PIP) install --upgrade pip setuptools wheel
	@echo "$(BLUE)Installing dependencies...$(NC)"
	$(VENV_PIP) install -e ".[dev]"
	@echo "$(GREEN)Installation complete! Activate venv with: $(VENV_BIN)/activate$(NC)"

test: ## Run unit and integration tests
	@echo "$(BLUE)Running tests...$(NC)"
	$(VENV_PYTHON) -m pytest tests/ -v --cov=src/bioetl --cov-report=term-missing --cov-report=html

test-unit: ## Run only unit tests (fast, no I/O)
	@echo "$(BLUE)Running unit tests...$(NC)"
	$(VENV_PYTHON) -m pytest tests/ -v -m unit

test-integration: ## Run integration tests
	@echo "$(BLUE)Running integration tests...$(NC)"
	$(VENV_PYTHON) -m pytest tests/ -v -m integration --vcr-record=none

test-e2e: ## Run E2E tests with Docker (requires docker-compose)
	@echo "$(BLUE)Starting Docker services...$(NC)"
	docker compose -f docker-compose.test.yml up -d
	@echo "$(BLUE)Waiting for services to be ready...$(NC)"
	@sleep 5
	@echo "$(BLUE)Running E2E tests...$(NC)"
	$(VENV_PYTHON) -m pytest tests/e2e/ -v -m e2e --tb=short || (docker compose -f docker-compose.test.yml down && exit 1)
	@echo "$(YELLOW)Stopping Docker services...$(NC)"
	docker compose -f docker-compose.test.yml down
	@echo "$(GREEN)E2E tests complete!$(NC)"

test-e2e-local: ## Run E2E tests (assumes Docker services already running)
	@echo "$(BLUE)Running E2E tests (using existing services)...$(NC)"
	$(VENV_PYTHON) -m pytest tests/e2e/ -v -m e2e --tb=short

test-watch: ## Run tests in watch mode
	$(VENV_PYTHON) -m pytest tests/ --looponfail

test-architecture: ## Run architecture enforcement tests
	@echo "$(BLUE)Running architecture tests...$(NC)"
	$(VENV_PYTHON) -m pytest tests/test_architecture_enforcement.py -v --tb=short
	@echo "$(GREEN)Architecture tests passed!$(NC)"

test-architecture-strict: ## Run architecture tests with import-linter
	@echo "$(BLUE)Running strict architecture checks...$(NC)"
	$(VENV_PYTHON) -m pytest tests/test_architecture_enforcement.py -v
	@echo "$(BLUE)Running import-linter...$(NC)"
	$(VENV_PYTHON) -m importlinter
	@echo "$(GREEN)All architecture checks passed!$(NC)"

lint: ## Run ruff and mypy
	@echo "$(BLUE)Running ruff...$(NC)"
	$(VENV_PYTHON) -m ruff check src/ tests/
	@echo "$(BLUE)Running mypy...$(NC)"
	$(VENV_PYTHON) -m mypy src/bioetl

lint-fix: ## Auto-fix linting issues
	@echo "$(BLUE)Auto-fixing with ruff...$(NC)"
	$(VENV_PYTHON) -m ruff check --fix src/ tests/
	$(VENV_PYTHON) -m ruff format src/ tests/

security: ## Run security audit (pip-audit)
	@echo "$(BLUE)Running security audit...$(NC)"
	$(VENV_PIP) audit --strict

docker-up: ## Start Docker Compose services (Postgres, Redis, MinIO)
	@echo "$(BLUE)Starting Docker services...$(NC)"
	docker compose up -d
	@echo "$(GREEN)Services started! Check with: docker compose ps$(NC)"

docker-down: ## Stop Docker Compose services
	@echo "$(YELLOW)Stopping Docker services...$(NC)"
	docker compose down

docker-reset: ## Stop services and remove volumes (clean slate)
	@echo "$(YELLOW)Resetting Docker environment...$(NC)"
	docker compose down -v
	@echo "$(GREEN)Docker environment reset!$(NC)"

docker-logs: ## Show logs from Docker services
	docker compose logs -f

seed-local: ## Load sample fixtures into local DB
	@echo "$(BLUE)Seeding local database...$(NC)"
	$(VENV_PYTHON) -m bioetl.interfaces.cli.seed --env local
	@echo "$(GREEN)Database seeded!$(NC)"

run-local: ## Run sample pipeline on local fixtures
	@echo "$(BLUE)Running sample pipeline...$(NC)"
	$(VENV_PYTHON) -m bioetl.interfaces.cli.runner --pipeline sample --env local

clean: ## Clean up generated files
	@echo "$(YELLOW)Cleaning up...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf htmlcov/ .coverage
	@echo "$(GREEN)Cleanup complete!$(NC)"

# Quarantine management (RULES.md §2.6)
quarantine-inspect: ## Inspect quarantine errors (PIPELINE=...)
	@echo "$(BLUE)Inspecting quarantine for $(PIPELINE)...$(NC)"
	$(VENV_PYTHON) -m bioetl.interfaces.cli.quarantine inspect --pipeline $(PIPELINE)

quarantine-replay: ## Replay quarantine records (PIPELINE=...)
	@echo "$(BLUE)Replaying quarantine for $(PIPELINE)...$(NC)"
	$(VENV_PYTHON) -m bioetl.interfaces.cli.quarantine replay --pipeline $(PIPELINE)

quarantine-purge: ## Purge quarantine (PIPELINE=...)
	@echo "$(YELLOW)Purging quarantine for $(PIPELINE)...$(NC)"
	$(VENV_PYTHON) -m bioetl.interfaces.cli.quarantine purge --pipeline $(PIPELINE)

# Lock management (RULES.md §3.3)
release-lock: ## Release stuck lock (PIPELINE=...)
	@echo "$(YELLOW)Releasing lock for $(PIPELINE)...$(NC)"
	$(VENV_PYTHON) -m bioetl.interfaces.cli.lock release --pipeline $(PIPELINE)

# Disaster Recovery (RULES.md §5.5)
dr-restore: ## Restore from backup (SCENARIO=..., DATE=...)
	@echo "$(BLUE)Running DR restore: scenario=$(SCENARIO), date=$(DATE)$(NC)"
	$(VENV_PYTHON) -m bioetl.interfaces.cli.dr restore --scenario $(SCENARIO) --date $(DATE)

# Rollback (RULES.md §7.2)
rollback: ## Rollback to version (VERSION=...)
	@echo "$(YELLOW)Rolling back to $(VERSION)...$(NC)"
	$(VENV_PYTHON) -m bioetl.interfaces.cli.rollback --version $(VERSION)

# Development helpers
dev-shell: ## Open Python shell with project context
	$(VENV_PYTHON) -i -c "from bioetl import *; print('BioETL dev shell ready!')"

watch-logs: ## Watch structured logs (tail -f)
	tail -f logs/bioetl.log | jq '.'

# Architecture and Quality Checks
arch-test: ## Run architecture tests (layer dependencies)
	@echo "$(BLUE)Running architecture tests...$(NC)"
	$(VENV_PYTHON) -m pytest tests/architecture/ -v

arch-lint: ## Run import-linter contracts
	@echo "$(BLUE)Checking import contracts...$(NC)"
	$(VENV_PYTHON) -m importlinter --config .importlinter

complexity: ## Check cyclomatic complexity (max CC=10)
	@echo "$(BLUE)Checking code complexity...$(NC)"
	$(VENV_PYTHON) -m xenon --max-absolute B --max-modules B --max-average A --exclude "tests/*" src/
	@echo "$(BLUE)Checking domain layer complexity (max CC=5)...$(NC)"
	$(VENV_PYTHON) -m xenon --max-absolute A --max-modules A --max-average A src/bioetl/domain/
	@echo "$(BLUE)Checking factories complexity (strict A/A/B)...$(NC)"
	$(VENV_PYTHON) -m xenon --max-absolute B --max-modules A --max-average A src/bioetl/interfaces/factories/

complexity-report: ## Generate detailed complexity report
	@echo "$(BLUE)Generating complexity report...$(NC)"
	mkdir -p reports
	$(VENV_PYTHON) -m radon cc src/ -a -s > reports/complexity.txt
	$(VENV_PYTHON) -m radon mi src/ -s >> reports/complexity.txt
	@echo "$(GREEN)Report saved to reports/complexity.txt$(NC)"

mutation-test: ## Run mutation testing (slow, domain layer only)
	@echo "$(BLUE)Running mutation testing on domain layer...$(NC)"
	$(VENV_PYTHON) -m mutmut run --paths-to-mutate=src/bioetl/domain/ --tests-dir=tests/

mutation-report: ## Show mutation testing results
	$(VENV_PYTHON) -m mutmut results

typecheck: ## Run strict type checking
	@echo "$(BLUE)Running mypy (strict)...$(NC)"
	$(VENV_PYTHON) -m mypy --config-file pyproject.toml src/bioetl

quality: lint arch-lint complexity typecheck ## Run all quality checks
	@echo "$(GREEN)All quality checks passed!$(NC)"

# CI/CD targets
ci-lint: lint security arch-lint ## Run all CI linting checks

ci-test: test arch-test ## Run all tests for CI

ci-quality: quality ## Run full quality gate

ci-build: ## Build distribution packages
	$(VENV_PYTHON) -m build

# Documentation
docs-serve: ## Serve documentation locally
	$(VENV_PYTHON) -m mkdocs serve

docs-build: ## Build documentation
	$(VENV_PYTHON) -m mkdocs build

# Version management
version: ## Show current version
	@$(VENV_PYTHON) -c "import bioetl; print(f'BioETL v{bioetl.__version__}')"

bump-version: ## Bump version (TYPE=major|minor|patch)
	$(VENV_PYTHON) -m bumpversion $(TYPE)

# Vendoring mermaid assets
vendor-mermaid: ## Download mermaid assets into assets/ (PowerShell on Windows)
	@echo "Running mermaid vendoring script..."
	@powershell.exe -NoProfile -ExecutionPolicy Bypass -File assets\javascripts\download_mermaid.ps1 -Version "10.4.0" || (echo "PowerShell vendoring failed; try running the script manually on a machine with network access" && exit 1)

check-mermaid: ## Check that vendored mermaid files exist (fails if missing)
	@echo "Checking vendored mermaid files..."
	@files="assets/javascripts/mermaid.min.js assets/javascripts/mermaid.esm.min.mjs assets/stylesheets/mermaid.css"; \
	missing=0; \
	for f in $$files; do \
		if [ ! -f $$f ]; then echo "MISSING: $$f"; missing=1; fi; \
	done; \
	if [ $$missing -eq 1 ]; then echo "Mermaid vendored assets missing; run 'make vendor-mermaid' locally or add the files to the PR"; exit 1; fi; \
	echo "Mermaid vendored assets present."
