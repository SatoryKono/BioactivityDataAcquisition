.PHONY: install test-deps setup-plugins precommit-install lint lint-fix lint-scripts-advisory quality-fast quality-pre-push quality-full clean clean-all clean-preflight clean-local-artifacts test run-local qa-arch-fast qa-arch-full qa-debt quarantine-inspect quarantine-replay quarantine-purge release-lock

PYTHON ?= python3
RUN ?= $(PYTHON) -m
PIPELINE ?=
RUN_ID ?=
RUN_LOCAL_PIPELINE ?= chembl_activity
RUN_LOCAL_LIMIT ?= 10
DRY_RUN ?= 0
PURGE_WORKTREES ?= 0

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
	$(RUN) pre_commit install --hook-type pre-commit --hook-type pre-push

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
	$(RUN) scripts.engineering.diagnostics cleanup $(CLEAN_APPLY_FLAG)
	@if [ -n "$(PURGE_WORKTREES_CMD)" ]; then $(PURGE_WORKTREES_CMD); fi

test:
	$(RUN) pytest

run-local:
	$(RUN) bioetl run --pipeline $(RUN_LOCAL_PIPELINE) --run-type incremental --limit $(RUN_LOCAL_LIMIT)

qa-arch-fast:
	$(RUN) pytest tests/architecture/test_future_annotations_policy.py tests/architecture/test_naming_conventions.py tests/architecture/test_no_structlog_in_application_interfaces.py tests/architecture/test_no_datetime_now_in_infrastructure.py tests/architecture/test_no_datetime_now_in_domain.py tests/architecture/test_replay_critical_time_seams.py tests/architecture/test_no_random_in_writers.py tests/architecture/test_forbidden_imports.py tests/architecture/test_domain_purity.py::TestDomainPurity::test_no_direct_io_in_domain tests/architecture/test_domain_normalization_guardrails.py::test_domain_normalization_modules_have_no_disallowed_runtime_imports tests/architecture/test_domain_normalization_guardrails.py::test_domain_normalization_modules_do_not_call_open -q --tb=short

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
