.PHONY: install test-deps setup-plugins lint lint-fix test run-local qa-arch-fast qa-arch-full qa-debt quarantine-inspect quarantine-replay quarantine-purge release-lock

PYTHON ?= python3
RUN ?= $(PYTHON) -m
PIPELINE ?=
RUN_ID ?=
RUN_LOCAL_PIPELINE ?= chembl_activity
RUN_LOCAL_LIMIT ?= 10

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

lint:
	$(RUN) ruff check src tests
	$(RUN) ruff format --check src tests
	$(RUN) mypy --config-file pyproject.toml --strict --no-incremental src/bioetl

lint-fix:
	$(RUN) ruff check --fix src tests
	$(RUN) ruff format src tests

test:
	$(RUN) pytest

run-local:
	$(RUN) bioetl run --pipeline $(RUN_LOCAL_PIPELINE) --run-type incremental --limit $(RUN_LOCAL_LIMIT)

qa-arch-fast:
	$(RUN) pytest tests/architecture/ -m "not slow and not serial and not memory"

qa-arch-full:
	$(RUN) pytest tests/architecture/ -m "not slow and not benchmark and not memory"

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
