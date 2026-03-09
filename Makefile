# BioETL Makefile
# Production-ready ETL system for bioactivity data

.PHONY: help install install-uv install-pip setup-plugins setup-skills test test-ci lint run-local docker-up docker-down docker-reset seed-local clean clean-local-artifacts sanitize-local clean-preflight clean-all diagram-preflight lint-diagrams report-diagrams-policy validate-diagrams-syntax render-diagrams render-diagrams-all render-diagrams-svg render-diagrams-png render-diagrams-descriptions-docx render-diagrams-descriptions-pdf run-diagram-docs-agent check-diagrams-visibility check-diagrams-pdf-bounds diagrams-all report-diagram-padding docs-lint docs-quality docs-docstrings docs-drift scripts-inventory-check scripts-inventory-update scripts-deprecation-report scripts-lifecycle-check scripts-catalog-check
.DEFAULT_GOAL := help

# Detect uv availability (preferred package manager)
UV_EXISTS := $(shell command -v uv 2> /dev/null)

# Python configuration
PYTHON := python3
VENV := .venv
ifeq ($(OS),Windows_NT)
	VENV_BIN := $(VENV)/Scripts
	VENV_PYTHON := $(VENV_BIN)/python.exe
	VENV_PIP := $(VENV_BIN)/pip.exe
else
	VENV_BIN := $(VENV)/bin
	VENV_PYTHON := $(VENV_BIN)/python
	VENV_PIP := $(VENV_BIN)/pip
endif

# Clear PYTHONPATH to avoid conflicts with other projects
export PYTHONPATH :=

# Use uv run if available, otherwise use venv python
ifdef UV_EXISTS
	RUN := uv run
	PY_RUN := uv run python
else
	RUN := $(VENV_PYTHON) -m
	PY_RUN := $(VENV_PYTHON)
endif

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)BioETL - Available Commands:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

install: ## Install dependencies (uses uv if available, otherwise pip)
ifdef UV_EXISTS
	@$(MAKE) install-uv
else
	@$(MAKE) install-pip
endif

install-uv: ## Install dependencies using uv (preferred)
	@echo "$(BLUE)Installing dependencies with uv...$(NC)"
	uv sync --extra dev --extra tracing
	@echo "$(GREEN)Installation complete! Run commands with: uv run <command>$(NC)"

install-pip: ## Install dependencies using pip (fallback)
	@echo "$(BLUE)Creating virtual environment...$(NC)"
	$(PYTHON) -m venv $(VENV)
	@echo "$(BLUE)Upgrading pip...$(NC)"
	$(VENV_PIP) install --upgrade pip setuptools wheel
	@echo "$(BLUE)Installing dependencies...$(NC)"
	$(VENV_PIP) install -e ".[dev,tracing]"
	@echo "$(GREEN)Installation complete! Activate venv with: source $(VENV_BIN)/activate$(NC)"

setup-dev: install test-deps-dev ## Full development environment setup and verification
	@echo "$(GREEN)Development environment setup and verified!$(NC)"

setup-plugins: ## Configure pytest/pre-commit plugins for local development
	@bash scripts/ops/setup_plugins.sh

setup-skills: ## Sync project Codex skills into CODEX_HOME (default: ~/.codex/skills)
	@bash scripts/ops/setup_skills.sh

test: test-deps-dev ## Run all tests serially with coverage (stable local default)
	@echo "$(BLUE)Running tests (serial default, excluding e2e and benchmarks)...$(NC)"
	$(RUN) pytest tests/ -p no:xdist -m "not e2e" --cov=src/bioetl --cov-report=term-missing --cov-fail-under=85

test-ci: test-deps-dev ## Run resilient CI flow (parallel + fallback + serial marker pass)
	@echo "$(BLUE)Running resilient CI test flow...$(NC)"
	$(PY_RUN) scripts/ci/run_pytest_resilient.py

test-serial: ## Run all tests serially (for debugging)
	@echo "$(BLUE)Running tests (serial mode)...$(NC)"
	$(RUN) pytest tests/ -v --cov=src/bioetl --cov-report=term-missing --cov-report=html --cov-fail-under=85

test-fast: ## Run fast tests only (no slow markers, CI hypothesis profile)
	@echo "$(BLUE)Running fast tests (parallel mode)...$(NC)"
	HYPOTHESIS_PROFILE=fast $(RUN) pytest tests/unit/ tests/architecture/ -n auto --dist loadscope --max-worker-restart=0 -m "not slow and not serial" --timeout=15 --ignore=tests/benchmarks

test-smoke: ## Run smoke tests (quick sanity check for local development)
	@echo "$(BLUE)Running smoke tests...$(NC)"
	$(RUN) pytest tests/smoke/ -v --tb=short
	@echo "$(GREEN)Smoke tests passed!$(NC)"

test-deps: ## Verify all runtime dependencies are importable
	@echo "$(BLUE)Checking runtime dependencies...$(NC)"
	$(RUN) pytest tests/smoke/test_smoke.py::TestRuntimeDependencies -v --tb=short
	@echo "$(GREEN)All dependencies OK!$(NC)"

test-deps-dev: test-deps ## Verify all development dependencies are importable
	@echo "$(BLUE)Checking development dependencies...$(NC)"
	$(RUN) pytest tests/smoke/test_smoke.py::TestDevDependencies -v --tb=short
	@echo "$(BLUE)Checking dev tools availability...$(NC)"
	$(RUN) ruff --version > /dev/null
	$(RUN) mypy --version > /dev/null
	@echo "$(GREEN)All development tools OK!$(NC)"

test-unit: ## Run only unit tests (parallel)
	@echo "$(BLUE)Running unit tests...$(NC)"
	$(RUN) pytest tests/unit/ -n auto --dist loadscope --max-worker-restart=0 -m "not serial" --ignore=tests/benchmarks

test-unit-fast: ## Run unit tests without slow tests (fastest)
	@echo "$(BLUE)Running fast unit tests...$(NC)"
	HYPOTHESIS_PROFILE=fast $(RUN) pytest tests/unit/ -n auto --dist loadscope --max-worker-restart=0 -m "not slow and not serial" --timeout=15 --ignore=tests/benchmarks

test-integration: ## Run integration tests with VCR
	@echo "$(BLUE)Running integration tests...$(NC)"
	$(RUN) pytest tests/integration/ -v --vcr-record=none

test-e2e: ## Run E2E tests with Docker (requires docker-compose)
	@echo "$(BLUE)Starting Docker services...$(NC)"
	docker compose -f docker-compose.test.yml up -d
	@echo "$(BLUE)Waiting for services to be ready...$(NC)"
	@sleep 5
	@echo "$(BLUE)Running E2E tests...$(NC)"
	$(RUN) pytest tests/e2e/ -v -m e2e --tb=short || (docker compose -f docker-compose.test.yml down && exit 1)
	@echo "$(YELLOW)Stopping Docker services...$(NC)"
	docker compose -f docker-compose.test.yml down
	@echo "$(GREEN)E2E tests complete!$(NC)"

test-e2e-local: ## Run E2E tests (assumes Docker services already running)
	@echo "$(BLUE)Running E2E tests (using existing services)...$(NC)"
	$(RUN) pytest tests/e2e/ -v -m e2e --tb=short

test-watch: ## Run tests in watch mode
	$(RUN) pytest tests/ --looponfail

test-profile: ## Profile test execution times (show top 50 slowest tests)
	@echo "$(BLUE)Profiling test execution times...$(NC)"
	$(RUN) pytest tests/ -q --durations=50 --durations-min=0.1 --ignore=tests/e2e/ --ignore=tests/benchmarks/
	@echo "$(GREEN)Profile complete!$(NC)"

test-ci-local: ## Run tests as they would run in CI (with HYPOTHESIS_PROFILE=ci)
	@echo "$(BLUE)Running CI-like tests locally...$(NC)"
	HYPOTHESIS_PROFILE=ci $(RUN) pytest tests/ -m "not e2e and not serial" -n auto --dist loadscope --max-worker-restart=0 --cov=src/bioetl --cov-fail-under=85

test-failed: ## Run only the tests that failed in the last run
	@echo "$(BLUE)Running failed tests...$(NC)"
	$(RUN) pytest tests/ -p no:xdist -v --lf

test-quick: ## Run quickest possible tests (fast profile, parallel, no slow tests)
	@echo "$(BLUE)Running quick tests (HYPOTHESIS_PROFILE=fast)...$(NC)"
	HYPOTHESIS_PROFILE=fast $(RUN) pytest tests/unit/ -m "not slow and not serial" -n auto --dist loadscope --max-worker-restart=0 -q --tb=line

test-changed: ## Run tests for changed files (compared to main branch)
	@echo "$(BLUE)Running tests for changed files...$(NC)"
	./scripts/dev/test_changed.sh

test-architecture: ## Run architecture enforcement tests
	@echo "$(BLUE)Running architecture tests...$(NC)"
	$(RUN) pytest tests/test_architecture_enforcement.py -v --tb=short
	@echo "$(GREEN)Architecture tests passed!$(NC)"

test-architecture-strict: ## Run architecture tests with import-linter
	@echo "$(BLUE)Running strict architecture checks...$(NC)"
	$(RUN) pytest tests/test_architecture_enforcement.py -v
	@echo "$(BLUE)Running import-linter...$(NC)"
	$(RUN) importlinter
	@echo "$(GREEN)All architecture checks passed!$(NC)"

lint: ## Run ruff and mypy
	@echo "$(BLUE)Running ruff...$(NC)"
	$(RUN) ruff check src/ tests/
	@echo "$(BLUE)Running mypy...$(NC)"
	$(RUN) mypy src/bioetl

lint-fix: ## Auto-fix linting issues
	@echo "$(BLUE)Auto-fixing with ruff...$(NC)"
	$(RUN) ruff check --fix src/ tests/
	$(RUN) ruff format src/ tests/

diagram-preflight: ## Check Mermaid render dependencies (mmdc required, svgo/rsvg optional)
	@echo "$(BLUE)Checking diagram toolchain...$(NC)"
	@command -v mmdc >/dev/null 2>&1 || (echo "$(YELLOW)mmdc missing. Install: npm install -g @mermaid-js/mermaid-cli$(NC)" && exit 1)
	@command -v svgo >/dev/null 2>&1 || echo "$(YELLOW)svgo missing (optional). Install: npm install -g svgo$(NC)"
	@command -v rsvg-convert >/dev/null 2>&1 || command -v inkscape >/dev/null 2>&1 || echo "$(YELLOW)rsvg-convert/inkscape missing (optional; PNG quality fallback to mmdc)$(NC)"
	@echo "$(GREEN)Diagram toolchain check complete.$(NC)"

lint-diagrams: ## Lint all Mermaid source files in docs/ (excluding docs/99-archive/**)
	@echo "$(BLUE)Linting diagram policies...$(NC)"
	$(PY_RUN) scripts/diagrams/lint_diagrams.py docs

report-diagrams-policy: ## Generate non-blocking diagram lint summary report
	@echo "$(BLUE)Generating diagram lint summary report...$(NC)"
	$(PY_RUN) scripts/diagrams/lint_diagrams.py docs/02-architecture/mmd-diagrams --json > /tmp/diagram-lint.json || true
	$(PY_RUN) scripts/diagrams/summarize_diagram_lint.py /tmp/diagram-lint.json

validate-diagrams-syntax: diagram-preflight ## Validate Mermaid syntax for docs/**/*.mmd|*.mermaid
	@echo "$(BLUE)Validating Mermaid syntax...$(NC)"
	bash scripts/diagrams/validate_mermaid_syntax.sh

render-diagrams-all: diagram-preflight ## Render all docs diagrams to SVG+PNG (excluding docs/99-archive/**)
	@echo "$(BLUE)Rendering all diagrams (SVG+PNG)...$(NC)"
	bash docs/02-architecture/mmd-diagrams/render.sh

render-diagrams: render-diagrams-all ## Backward-compatible alias for full diagram rendering

render-diagrams-svg: diagram-preflight ## Render all docs diagrams to SVG only
	@echo "$(BLUE)Rendering all diagrams (SVG only)...$(NC)"
	bash docs/02-architecture/mmd-diagrams/render.sh --svg-only

render-diagrams-png: diagram-preflight ## Render all docs diagrams to PNG only
	@echo "$(BLUE)Rendering all diagrams (PNG only)...$(NC)"
	bash docs/02-architecture/mmd-diagrams/render.sh --png-only

render-diagrams-descriptions-pdf: ## Generate *-with-descriptions.pdf bundles with print-safe fit and bounds check
	@echo "$(BLUE)Generating diagram description PDFs...$(NC)"
	$(PY_RUN) scripts/diagrams/generate_with_descriptions_pdf.py

render-diagrams-descriptions-docx: ## Generate *-with-descriptions.docx bundles from Markdown
	@echo "$(BLUE)Generating diagram description DOCX...$(NC)"
	$(PY_RUN) scripts/diagrams/generate_with_descriptions_docx.py

run-diagram-docs-agent: ## Full diagram docs pipeline (checks + docx + pdf)
	@echo "$(BLUE)Running diagram docs agent pipeline...$(NC)"
	bash scripts/diagrams/run_diagram_docs_agent.sh

check-diagrams-pdf-bounds: ## Validate existing with-descriptions PDF bundles for image clipping/overflow
	@echo "$(BLUE)Checking with-descriptions PDF bounds...$(NC)"
	$(PY_RUN) scripts/diagrams/check_pdf_image_bounds.py --pdf docs/02-architecture/mmd-diagrams/class-diagrams-with-descriptions.pdf
	$(PY_RUN) scripts/diagrams/check_pdf_image_bounds.py --pdf docs/02-architecture/mmd-diagrams/foundation-diagrams-with-descriptions.pdf

check-diagrams-visibility: ## Check text visibility in baseline SVG smoke set
	@echo "$(BLUE)Checking SVG text visibility (smoke manifest)...$(NC)"
	$(PY_RUN) scripts/diagrams/check_svg_text_visibility.py --manifest docs/02-architecture/mmd-diagrams/visual-smoke-manifest.txt

diagrams-all: lint-diagrams validate-diagrams-syntax render-diagrams-all check-diagrams-visibility ## Full diagram pipeline (lint + validate + render + visibility check)
	@echo "$(GREEN)Diagram pipeline complete.$(NC)"

report-diagram-padding: ## Report top files by &nbsp; usage in Mermaid sources
	@echo "$(BLUE)Reporting Mermaid &nbsp; usage...$(NC)"
	$(PY_RUN) scripts/diagrams/report_diagram_padding.py --top 30

security: ## Run security audit (osv-scanner + pip-audit)
	@echo "$(BLUE)Running security audit...$(NC)"
	@echo "$(BLUE)Running osv-scanner (primary, supports uv.lock)...$(NC)"
	@which osv-scanner >/dev/null 2>&1 && osv-scanner scan . || echo "$(YELLOW)osv-scanner not installed. Install from: https://github.com/google/osv-scanner$(NC)"
	@echo "$(BLUE)Running pip-audit (secondary, skips local package)...$(NC)"
	$(RUN) pip-audit --skip-editable

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

monitoring-up: ## Start monitoring services (Prometheus + Grafana)
	@echo "$(BLUE)Starting monitoring services...$(NC)"
	docker compose -f docker-compose.monitoring.yml up -d
	@echo "$(GREEN)Monitoring started! Grafana: http://localhost:3000 (admin/admin)$(NC)"

monitoring-down: ## Stop monitoring services
	@echo "$(YELLOW)Stopping monitoring services...$(NC)"
	docker compose -f docker-compose.monitoring.yml down

monitoring-logs: ## Show logs from monitoring services
	docker compose -f docker-compose.monitoring.yml logs -f

seed-local: ## Load sample fixtures into local DB
	@echo "$(YELLOW)Note: BioETL uses external APIs - no local seeding required$(NC)"
	@echo "$(GREEN)Ready for pipeline run!$(NC)"

run-local: ## Run sample pipeline (ChEMBL activity with limit)
	@echo "$(BLUE)Running ChEMBL activity pipeline (limit=10)...$(NC)"
	$(RUN) bioetl run --pipeline chembl_activity --limit 10

clean: ## Clean up generated files (Python artifacts, caches, build outputs)
	@echo "$(YELLOW)Cleaning Python artifacts...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	rm -rf build/ dist/ htmlcov/ .coverage .coverage.* coverage.xml 2>/dev/null || true
	@echo "$(GREEN)Cleanup complete!$(NC)"

clean-local-artifacts: ## Clean local-only artifacts in repo root (use DRY_RUN=1, PURGE_WORKTREES=1)
	@echo "$(YELLOW)Cleaning local-only artifacts (DRY_RUN=$(DRY_RUN), PURGE_WORKTREES=$(PURGE_WORKTREES))...$(NC)"
	@set -eu; \
	remove_cmd="rm -rf"; \
	remove_file_cmd="rm -f"; \
	if [ "$(DRY_RUN)" = "1" ]; then \
		remove_cmd="echo [DRY_RUN] rm -rf"; \
		remove_file_cmd="echo [DRY_RUN] rm -f"; \
	else \
		$(MAKE) clean; \
	fi; \
	$$remove_cmd site docs/site .mkdocs-site-tmp htmlcov .mypy_cache .pytest_cache .ruff_cache .hypothesis .benchmarks .import_linter_cache; \
	$$remove_file_cmd bash.exe.stackdump full_log.txt log_test.txt coverage_output.txt coverage_summary.txt profile.svg; \
	find . -maxdepth 1 -type f \( -name "test_backfill_*" -o -name "test_chembl_*" -o -name "test_failed_*" -o -name "test_full_pipeline_*" -o -name "test_multiple_*" -o -name "test_pipeline_*" -o -name "test_pubchem_*" -o -name "test_pubmed_*" -o -name "test_uniprot_*" -o -name "test_crossref_*" -o -name "Test*.test_*" -o -name "test_rebuild_*" -o -name "test_run_type_*" -o -name "test_vacuum_*" -o -name "*.stackdump" \) -print | while read -r f; do $$remove_file_cmd "$$f"; done; \
	if [ "$(PURGE_WORKTREES)" = "1" ]; then \
		echo "$(YELLOW)Purging .worktrees and .rollback directories$(NC)"; \
		$$remove_cmd .worktrees .rollback; \
	else \
		echo "$(BLUE)Skipping .worktrees/.rollback purge (set PURGE_WORKTREES=1 to enable)$(NC)"; \
	fi
	@echo "$(GREEN)Local artifact cleanup complete!$(NC)"

sanitize-local: ## Deep local sanitation (set PURGE_WORKTREES=1 to drop .worktrees/.rollback)
	$(MAKE) clean-local-artifacts PURGE_WORKTREES=$(PURGE_WORKTREES)
	$(PY_RUN) scripts/data/check_root_vcr_cassettes.py
	$(PY_RUN) scripts/data/check_vcr_filename_policy.py
	$(PY_RUN) scripts/repo/audit_root_cleanliness.py --strict-untracked


clean-preflight: ## Clean preflight artifacts (use DRY_RUN=1 for preview)
	@echo "$(YELLOW)Running preflight cleanup...$(NC)"
	@if [ "$(DRY_RUN)" = "1" ]; then \
		bash scripts/repo/preflight_cleanup.sh --dry-run; \
	else \
		bash scripts/repo/preflight_cleanup.sh; \
	fi

clean-all: clean ## Clean all (artifacts + logs + temp files)
	@echo "$(YELLOW)Cleaning logs and temporary files...$(NC)"
	find . -type f -name "*.log" -delete 2>/dev/null || true
	find . -type f -name "*.tmp" -delete 2>/dev/null || true
	rm -f full_log.txt final_report*.txt project_rules_failures.txt 2>/dev/null || true
	@echo "$(GREEN)Full cleanup complete!$(NC)"

# Quarantine management (RULES.md §2.6)
quarantine-inspect: ## Inspect quarantine errors (PIPELINE=...)
	@echo "$(BLUE)Inspecting quarantine for $(PIPELINE)...$(NC)"
	$(RUN) bioetl.interfaces.cli.quarantine inspect --pipeline $(PIPELINE)

quarantine-replay: ## Replay quarantine records (PIPELINE=...)
	@echo "$(BLUE)Replaying quarantine for $(PIPELINE)...$(NC)"
	$(RUN) bioetl.interfaces.cli.quarantine replay --pipeline $(PIPELINE)

quarantine-purge: ## Purge quarantine (PIPELINE=...)
	@echo "$(YELLOW)Purging quarantine for $(PIPELINE)...$(NC)"
	$(RUN) bioetl.interfaces.cli.quarantine purge --pipeline $(PIPELINE)

# Lock management (RULES.md §3.3)
release-lock: ## Release stuck lock (PIPELINE=...)
	@echo "$(YELLOW)Releasing lock for $(PIPELINE)...$(NC)"
	$(RUN) bioetl.interfaces.cli.lock release --pipeline $(PIPELINE)

# Disaster Recovery (RULES.md §5.5)
dr-restore: ## Restore from backup (SCENARIO=..., DATE=...)
	@echo "$(BLUE)Running DR restore: scenario=$(SCENARIO), date=$(DATE)$(NC)"
	$(RUN) bioetl.interfaces.cli.dr restore --scenario $(SCENARIO) --date $(DATE)

# Rollback (RULES.md §7.2)
rollback: ## Rollback to version (VERSION=...)
	@echo "$(YELLOW)Rolling back to $(VERSION)...$(NC)"
	$(RUN) bioetl.interfaces.cli.rollback --version $(VERSION)

# Development helpers
dev-shell: ## Open Python shell with project context
ifdef UV_EXISTS
	uv run python -i -c "from bioetl import *; print('BioETL dev shell ready!')"
else
	$(VENV_PYTHON) -i -c "from bioetl import *; print('BioETL dev shell ready!')"
endif

profile: ## Run pipeline with py-spy (PIPELINE=...)
	@echo "$(BLUE)Profiling pipeline $(PIPELINE)...$(NC)"
ifdef UV_EXISTS
	uv run py-spy record -o profile.svg -- uv run bioetl run --pipeline $(PIPELINE)
else
	$(VENV_BIN)/py-spy record -o profile.svg -- $(VENV_PYTHON) -m bioetl.interfaces.cli run --pipeline $(PIPELINE)
endif

watch-logs: ## Watch structured logs (tail -f)
	tail -f logs/bioetl.log | jq '.'

# Architecture and Quality Checks
arch-test: ## Run architecture tests (layer dependencies, determinism)
	@echo "$(BLUE)Running architecture tests...$(NC)"
	$(RUN) pytest tests/architecture/ -v --tb=short
	@echo "$(GREEN)Architecture tests passed!$(NC)"

arch-lint: ## Run import-linter contracts
	@echo "$(BLUE)Checking import contracts...$(NC)"
	$(RUN) importlinter --config .importlinter

arch-all: arch-lint arch-test ## Run all architecture checks (lint + tests)
	@echo "$(GREEN)All architecture checks passed!$(NC)"

complexity: ## Check cyclomatic complexity (max CC=10)
	@echo "$(BLUE)Checking code complexity...$(NC)"
	$(RUN) xenon --max-absolute B --max-modules B --max-average A --exclude "tests/*" src/
	@echo "$(BLUE)Checking domain layer complexity (max CC=5)...$(NC)"
	$(RUN) xenon --max-absolute A --max-modules A --max-average A src/bioetl/domain/
	@echo "$(BLUE)Checking adapters complexity (max CC=5)...$(NC)"
	$(RUN) xenon --max-absolute A --max-modules A --max-average A src/bioetl/infrastructure/adapters/
	@echo "$(BLUE)Checking factories complexity (strict A/A/B)...$(NC)"
	$(RUN) xenon --max-absolute B --max-modules A --max-average A src/bioetl/interfaces/factories/

check-duplication: ## Check for code duplication
	@echo "$(BLUE)Checking code duplication...$(NC)"
	$(RUN) pylint --disable=all --enable=duplicate-code src/bioetl/infrastructure/adapters

complexity-report: ## Generate detailed complexity report
	@echo "$(BLUE)Generating complexity report...$(NC)"
	mkdir -p reports
	$(RUN) radon cc src/ -a -s > reports/complexity.txt
	$(RUN) radon mi src/ -s >> reports/complexity.txt
	@echo "$(GREEN)Report saved to reports/complexity.txt$(NC)"

bench: ## Run all benchmark tests (standalone + assertion-based + performance)
	@echo "$(BLUE)Running all benchmarks...$(NC)"
	@mkdir -p reports
	$(RUN) pytest benchmarks/ tests/benchmarks/ tests/performance/ -v --tb=short -m benchmark
	@echo "$(GREEN)Benchmarks complete!$(NC)"

bench-standalone: ## Run only pytest-benchmark standalone tests
	@echo "$(BLUE)Running standalone benchmarks...$(NC)"
	@mkdir -p reports
	$(RUN) pytest benchmarks/ -v --tb=short
	@echo "$(GREEN)Standalone benchmarks complete!$(NC)"

bench-json: ## Run benchmarks with JSON output (pytest-benchmark only)
	@echo "$(BLUE)Running benchmarks with JSON output...$(NC)"
	@mkdir -p reports
	$(RUN) pytest benchmarks/ -v --benchmark-only --benchmark-json=reports/benchmark.json 2>/dev/null || \
		$(RUN) pytest benchmarks/ -v --tb=short
	@echo "$(GREEN)Benchmarks complete! Results in reports/benchmark.json$(NC)"

bench-baselines: ## Run assertion-based benchmark baseline tests
	@echo "$(BLUE)Running baseline assertion benchmarks...$(NC)"
	$(RUN) pytest tests/benchmarks/ tests/performance/ -v --tb=short -m benchmark
	@echo "$(GREEN)Baseline benchmarks complete!$(NC)"

mutation-test: ## Run mutation testing (slow, domain layer only)
	@echo "$(BLUE)Running mutation testing on domain layer...$(NC)"
	$(RUN) mutmut run --paths-to-mutate=src/bioetl/domain/ --tests-dir=tests/

mutation-report: ## Show mutation testing results
	$(RUN) mutmut results

typecheck: ## Run strict type checking
	@echo "$(BLUE)Running mypy (strict)...$(NC)"
	$(RUN) mypy --config-file pyproject.toml src/bioetl

quality: lint arch-lint complexity typecheck ## Run all quality checks
	@echo "$(GREEN)All quality checks passed!$(NC)"

# CI/CD targets
ci: lint test arch-all ## Run complete CI pipeline (lint + test + architecture)
	@echo "$(GREEN)CI checks complete!$(NC)"

ci-lint: lint security arch-lint ## Run all CI linting checks

ci-test: test arch-all ## Run all tests for CI (includes architecture checks)

ci-quality: quality ## Run full quality gate

ci-build: ## Build distribution packages
	$(RUN) build

# Documentation
docs-serve: ## Serve documentation locally
	$(RUN) mkdocs serve --site-dir .mkdocs-site-tmp

docs-build: ## Build documentation
	$(RUN) bash scripts/docs/build_docs_site.sh

docs-lint: ## Run documentation guardrails (links + config conventions + drift checks)
	$(PY_RUN) scripts/docs/check_doc_links.py --links
	$(PY_RUN) scripts/docs/check_doc_links.py --configs
	$(PY_RUN) scripts/docs/check_doc_links.py --legacy-paths

docs-docstrings: ## Check docstring coverage (modules ≥100%, classes ≥95%, functions ≥90%)
	@echo "$(BLUE)Checking docstring coverage...$(NC)"
	$(PY_RUN) scripts/docs/check_docstring_coverage.py
	@echo "$(GREEN)Docstring coverage check complete!$(NC)"

docs-drift: ## Detect documentation drift (code ↔ docs synchronization)
	@echo "$(BLUE)Running documentation drift detection...$(NC)"
	$(PY_RUN) scripts/docs/check_doc_drift.py
	@echo "$(GREEN)Drift detection complete!$(NC)"

scripts-inventory-check: ## Check scripts inventory manifest drift
	@echo "$(BLUE)Checking scripts inventory drift...$(NC)"
	$(PY_RUN) scripts/repo/check_scripts_inventory.py --check --manifest configs/quality/scripts_inventory_manifest.json
	@echo "$(GREEN)Scripts inventory is in sync!$(NC)"

scripts-inventory-update: ## Update scripts inventory manifest
	@echo "$(BLUE)Updating scripts inventory manifest...$(NC)"
	$(PY_RUN) scripts/repo/check_scripts_inventory.py --update --manifest configs/quality/scripts_inventory_manifest.json
	@echo "$(GREEN)Scripts inventory manifest updated!$(NC)"

scripts-deprecation-report: ## Generate staged deprecation backlog for non-active scripts
	@echo "$(BLUE)Generating scripts deprecation backlog...$(NC)"
	$(PY_RUN) scripts/repo/check_scripts_inventory.py --deprecation-report reports/quality/scripts_deprecation_backlog.md
	@echo "$(GREEN)Scripts deprecation backlog updated!$(NC)"

scripts-lifecycle-check: ## Validate lifecycle registry coverage for non-active scripts
	@echo "$(BLUE)Validating scripts lifecycle registry...$(NC)"
	$(PY_RUN) scripts/repo/check_scripts_inventory.py --check-lifecycle --forbid-evaluate-active --lifecycle-registry configs/quality/scripts_lifecycle_registry.json
	@echo "$(GREEN)Scripts lifecycle registry is valid!$(NC)"

scripts-catalog-check: ## Validate scripts catalog governance policy
	@echo "$(BLUE)Validating scripts catalog governance...$(NC)"
	$(PY_RUN) scripts/repo/check_scripts_catalog.py --catalog scripts/catalog.yaml
	@echo "$(GREEN)Scripts catalog governance is valid!$(NC)"

docs-quality: docs-lint docs-docstrings docs-drift scripts-inventory-check scripts-lifecycle-check scripts-catalog-check ## Run all documentation quality checks
	@echo "$(GREEN)All documentation quality checks passed!$(NC)"

schema-artifacts: ## Generate canonical schema artifacts (registry + contracts)
	@echo "$(BLUE)Generating schema artifacts...$(NC)"
	$(RUN) python scripts/schema/generate_schema_artifacts.py
	@echo "$(GREEN)Schema artifacts generated!$(NC)"

contracts-check: ## Generate and check data contracts
	@echo "$(BLUE)Generating data contracts...$(NC)"
ifdef UV_EXISTS
	uv run python scripts/schema/generate_contracts.py
else
	$(VENV_PYTHON) scripts/schema/generate_contracts.py
endif
	@echo "$(GREEN)Contracts generated!$(NC)"

# Version management
version: ## Show current version
ifdef UV_EXISTS
	@uv run python -c "import bioetl; print(f'BioETL v{bioetl.__version__}')"
else
	@$(VENV_PYTHON) -c "import bioetl; print(f'BioETL v{bioetl.__version__}')"
endif

bump-version: ## Bump version (TYPE=major|minor|patch)
	$(RUN) bumpversion $(TYPE)

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


schema-artifacts-check: ## Verify generated schema artifacts are up-to-date
	@echo "$(BLUE)Checking schema artifacts...$(NC)"
	$(RUN) python scripts/schema/generate_schema_artifacts.py --check
	@echo "$(GREEN)Schema artifacts are up-to-date!$(NC)"
