.PHONY: install test-deps setup-plugins precommit-install lint lint-fix lint-scripts-advisory quality-fast quality-pre-push quality-full clean clean-all clean-preflight clean-local-artifacts test test-fast test-unit test-integration test-architecture test-smoke test-serial test-cov-fast-stable test-ci run-local qa-arch-fast qa-arch-full qa-debt quarantine-inspect quarantine-replay quarantine-purge release-lock

PYTHON ?= python3
RUN ?= $(PYTHON) -m
PIPELINE ?=
RUN_ID ?=
RUN_LOCAL_PIPELINE ?= chembl_activity
RUN_LOCAL_LIMIT ?= 10
DRY_RUN ?= 0
PURGE_WORKTREES ?= 0
LOCAL_COV_FAIL_UNDER ?= 80

ifeq ($(filter 1 true yes TRUE YES,$(DRY_RUN)),)
	CLEAN_APPLY_FLAG := --apply
else
	CLEAN_APPLY_FLAG :=
endif

ifeq ($(filter 1 true yes TRUE YES,$(PURGE_WORKTREES)),)
	PURGE_WORKTREES_CMD :=
else
	PURGE_WORKTREES_CMD := rm -rf .worktrees .rollback
endif

install:
	@if command -v uv >/dev/null 2>&1; then \
		uv sync --extra dev --extra tests --extra tracing; \
	else \
		$(RUN) pip install -e ".[dev,tests,tracing]"; \
	fi

test-deps:
	bash scripts/ops/launchers/codex/setup_plugins.sh --pytest-only

setup-plugins:
	bash scripts/ops/launchers/codex/setup_plugins.sh

precommit-install:
	bash scripts/ops/launchers/codex/setup_plugins.sh --hooks-only

lint:
	$(RUN) ruff check src tests
	$(RUN) ruff format --check src tests
	$(RUN) mypy --config-file pyproject.toml --strict --no-incremental src/bioetl

lint-fix:
	$(RUN) ruff check --fix src tests
	$(RUN) ruff format src tests

lint-scripts-advisory:
	$(RUN) ruff check scripts --exit-zero

quality-fast:
	$(RUN) pre_commit run --hook-stage pre-commit --all-files

quality-pre-push:
	$(RUN) pre_commit run --hook-stage pre-push --all-files

quality-full:
	$(RUN) pre_commit run --all-files

clean:
	$(RUN) scripts.engineering.diagnostics cleanup $(CLEAN_APPLY_FLAG)

clean-all:
	$(RUN) scripts.engineering.diagnostics cleanup $(CLEAN_APPLY_FLAG) --purge-logs

clean-preflight:
	$(RUN) scripts.engineering.repo preflight-cleanup $(if $(filter 1 true yes TRUE YES,$(DRY_RUN)),--dry-run)

clean-local-artifacts:
	$(RUN) scripts.engineering.diagnostics cleanup $(CLEAN_APPLY_FLAG) --purge-logs
	@$(if $(PURGE_WORKTREES_CMD),$(PURGE_WORKTREES_CMD),:)

test:
	$(RUN) scripts.engineering.qa run-tests --suite coverage-verify --skip-preflight

test-fast:
	$(RUN) scripts.engineering.qa run-tests --suite unit-fast --skip-preflight

test-unit: test-fast

test-integration:
	$(RUN) scripts.engineering.qa run-tests --suite integration-replay --skip-preflight

test-architecture: qa-arch-full

test-smoke:
	$(RUN) scripts.engineering.qa run-tests --suite smoke --skip-preflight

test-serial:
	$(RUN) pytest tests/ -m "serial and not e2e and not benchmark and not memory" -q --tb=short -p no:xdist

test-cov-fast-stable:
	BIOETL_PYTEST_SHARDED_FORCE_COVERAGE=1 bash scripts/engineering/dev/run_pytest_sharded.sh --stream --keep-coverage-files --coverage-dir .coverage-sharded -- -m "not e2e and not benchmark and not memory" --cov=src/bioetl --cov-report=term-missing --cov-fail-under=$(LOCAL_COV_FAIL_UNDER)

test-ci:
	$(RUN) scripts.engineering.ci run-tests

run-local:
	$(RUN) bioetl run --pipeline $(RUN_LOCAL_PIPELINE) --run-type incremental --limit $(RUN_LOCAL_LIMIT)

qa-arch-fast:
	$(RUN) pytest tests/architecture/ -m "not slow and not serial and not memory" -q --tb=short

qa-arch-full:
	$(RUN) pytest tests/architecture/ -m "not slow and not benchmark and not memory" -q --tb=short

qa-debt:
	$(RUN) scripts.engineering.qa.check_quality_exemptions --trend-report on

quarantine-inspect:
	$(RUN) bioetl quarantine inspect --pipeline $(PIPELINE)

quarantine-replay:
	$(RUN) bioetl quarantine replay --pipeline $(PIPELINE)

quarantine-purge:
	$(RUN) bioetl quarantine purge --pipeline $(PIPELINE)

release-lock:
	$(RUN) bioetl lock release --pipeline $(PIPELINE) --run-id $(RUN_ID)

antigravity:
	@export BROWSER='/mnt/c/Windows/System32/cmd.exe /c start' && $(RUN) antigravity
