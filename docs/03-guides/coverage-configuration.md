______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Coverage Configuration Guide

**Reference**: `pyproject.toml [tool.coverage.*]` sections (lines 203-229)
**Last Updated**: 2026-03-26

______________________________________________________________________

## Overview

BioETL uses `pytest-cov` (Coverage.py) to measure code test coverage with a **85% threshold** enforced in CI.
The configuration balances executable code metrics with realistic coverage targets, excluding stub-like code that cannot be tested.

______________________________________________________________________

## Configuration File

**Location**: `pyproject.toml`

```toml
# ============ COVERAGE ============
[tool.coverage.run]
source = ["src/bioetl"]
branch = true
omit = [
    "*/tests/*",
    "*/__pycache__/*",
    "*/__main__.py",  # Entry point modules - minimal code, tested via CLI tests
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",      # Explicit coverage skip
    "if TYPE_CHECKING:",     # Type-only imports
    "raise NotImplementedError",  # Abstract methods
    "@abstractmethod",       # ABC marker
    "@overload",             # Protocol/typing stubs (P3 update)
    "^\\s*pass\\s*$",        # Bare pass statements (P3 update)
    "^\\s*\\.\\.\\.\\s*$",   # Ellipsis stubs (P3 update)
]
show_missing = true
precision = 2
# Note: fail_under NOT set here (CI coverage-verify uses --cov-fail-under=85)
```

______________________________________________________________________

## Key Settings

### `[tool.coverage.run]`

| Setting  | Value                                    | Purpose                                      |
| -------- | ---------------------------------------- | -------------------------------------------- |
| `source` | `["src/bioetl"]`                         | Only measure production code                 |
| `branch` | `true`                                   | Include branch coverage (condition coverage) |
| `omit`   | Test files, `__pycache__`, `__main__.py` | Exclude non-measurable code                  |

**Note**: `fail_under` is NOT set here because CI test-matrix runs parallel groups that cover partial codebase. The `coverage-verify` step in `.github/workflows/tests.yml` explicitly uses `--cov-fail-under=85`.

### `[tool.coverage.report]`

#### exclude_lines (Exclude Patterns)

Lines matching these patterns are excluded from coverage metrics:

| Pattern                     | Use Case                     | Example                                            |
| --------------------------- | ---------------------------- | -------------------------------------------------- |
| `pragma: no cover`          | Manual exclusion marker      | `if unreachable:  # pragma: no cover`              |
| `if TYPE_CHECKING:`         | Type-only imports            | `if TYPE_CHECKING: from typing import ...`         |
| `raise NotImplementedError` | Abstract method placeholders | `def abstract_method(): raise NotImplementedError` |
| `@abstractmethod`           | ABC decorators               | Inherent placeholder in abstract classes           |
| `@overload`                 | Protocol stubs (P3)          | Type-checking-only method signatures in Protocols  |
| `^\\s*pass\\s*$`            | Bare pass statements (P3)    | No-op placeholders in abstract classes             |
| `^\\s*\\.\\.\\.\\s*$`       | Ellipsis stubs (P3)          | Protocol method implementations                    |

**P3 Update (2026-03-08)**: Added 3 patterns (`@overload`, bare `pass`, ellipsis) to exclude non-executable stub-like code from coverage metrics. This allows focusing metrics on actual executable code paths.

#### Other Settings

| Setting        | Value  | Purpose                             |
| -------------- | ------ | ----------------------------------- |
| `show_missing` | `true` | List uncovered lines in report      |
| `precision`    | `2`    | Two decimal places (e.g., `85.42%`) |

______________________________________________________________________

## Running Coverage Checks

### Local Development

```bash
# Stable full local run with enforced 85% threshold
make test

# Faster split coverage run (defaults to 80% unless LOCAL_COV_FAIL_UNDER is overridden)
make test-cov-fast-stable

# Generate HTML report after a coverage-producing run
uv run coverage html -d htmlcov
```

Notes:

- `make test` is the stable serial default and enforces `--cov-fail-under=85`;
- `make test-cov-fast-stable` is the local optimization path and defaults to `LOCAL_COV_FAIL_UNDER=80`;
- `htmlcov/` is not produced automatically by `make test`.

### CI Validation

```bash
# Serial subset for coverage-verify
COVERAGE_FILE=reports/coverage/.coverage.serial uv run python scripts/engineering/ci/run_pytest_resilient.py \
  --target tests/ \
  --reports-dir reports/pytest/coverage-verify \
  --parallel-marker "serial and not e2e and not benchmark" \
  --parallel-addopts "-q --tb=short -p no:xdist --ignore=tests/e2e --ignore=tests/contract --cov=src/bioetl --cov-report=" \
  --skip-serial-pass

# Final combine + threshold
uv run python -m coverage combine --keep reports/coverage
uv run python -m coverage report --show-missing --fail-under=85
```

Coverage CI check runs in `.github/workflows/tests.yml` → `coverage-verify` job.

______________________________________________________________________

## Understanding Exclude Patterns

### Example 1: Protocol with `@overload`

```python
from typing import Protocol, overload, AsyncIterator


@runtime_checkable
class DataSourcePort(Protocol):
    """Contract for data sources."""

    @overload
    def fetch(self, entity_type: str) -> AsyncIterator[dict[str, Any]]: ...

    @overload
    def fetch(
        self,
        entity_type: str,
        limit: int,
    ) -> AsyncIterator[dict[str, Any]]: ...

    async def fetch(
        self,
        entity_type: str,
        limit: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Actual implementation (tested)."""
        ...
```

**Coverage Behavior**:

- Lines with `@overload` decorator → **EXCLUDED** (type-only)
- Line with actual `async def fetch(...)` → **INCLUDED** (executable)
- Ellipsis in actual implementation → **EXCLUDED** (optional; stub-like)

______________________________________________________________________

### Example 2: Abstract Base Class with `pass`

```python
from abc import ABC, abstractmethod


class AbstractService(ABC):
    """Abstract service (not tested directly)."""

    @abstractmethod
    def start(self) -> None:
        pass  # EXCLUDED (bare pass)

    @abstractmethod
    def stop(self) -> None: ...  # EXCLUDED (ellipsis)
```

**Coverage Behavior**:

- `@abstractmethod` decorator → **EXCLUDED**
- `pass` statement → **EXCLUDED** (bare pass pattern)
- Ellipsis → **EXCLUDED** (ellipsis pattern)

Subclass implementations are tested directly and count toward coverage.

______________________________________________________________________

### Example 3: Type-Only Imports

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # These imports are EXCLUDED from coverage
    from some_expensive_module import SomeType  # EXCLUDED


def function(x: "SomeType") -> None:
    # This implementation IS INCLUDED
    print(x)
```

______________________________________________________________________

## Coverage Targets

| Layer              | Target | Notes                                           |
| ------------------ | ------ | ----------------------------------------------- |
| **Domain**         | >90%   | Core business logic; highest priority           |
| **Application**    | >85%   | Pipelines, transformers                         |
| **Infrastructure** | >80%   | Adapters, storage (lower due to I/O complexity) |
| **Overall**        | ≥85%   | CI enforcement threshold                        |

______________________________________________________________________

## Troubleshooting

### Low Coverage on Protocols

**Problem**: Protocol definitions show low coverage despite being well-tested.

**Solution**: Protocol methods with `@overload`, `pass`, or `...` are automatically excluded. Ensure concrete implementations are tested.

### False Coverage Gaps

**Problem**: Legitimate code showing as "missing" in HTML report.

**Solution**: Use `# pragma: no cover` to manually exclude unreachable code:

```python
if sys.platform == "win32":  # Only reachable on Windows
    handle_windows()
else:  # pragma: no cover
    handle_unix()
```

### Coverage Fluctuation in CI

**Problem**: Coverage varies between local runs and CI.

**Possible Causes**:

1. Different Python versions (3.11 vs 3.12) — conditional code paths differ
1. Partial test runs in parallel CI — coverage is cumulative across all jobs
1. Missing test dependencies — some tests skipped

**Solution**: Run the full suite locally only when needed; in CI coverage is now
assembled from shard coverage plus a dedicated `serial` pass, rather than from
one extra full rerun of almost the entire suite.

______________________________________________________________________

## CI Integration

### Workflow: `tests.yml`

**Job**: `coverage-verify`

```yaml
coverage-verify:
  needs: [smoke-check, test-fast, test-matrix]
  runs-on: ubuntu-latest
  steps:
    - uses: actions/download-artifact@v4
      with:
        pattern: coverage-data-*
        merge-multiple: true
        path: reports/coverage
    - run: >
        COVERAGE_FILE=reports/coverage/.coverage.serial uv run python
        scripts/engineering/ci/run_pytest_resilient.py
        --target tests/
        --reports-dir reports/pytest/coverage-verify
        --parallel-marker "serial and not e2e and not benchmark"
        --parallel-addopts "-q --tb=short -p no:xdist --ignore=tests/e2e --ignore=tests/contract --cov=src/bioetl --cov-report="
        --skip-serial-pass
    - run: uv run python -m coverage combine --keep reports/coverage
    - run: uv run python -m coverage report --show-missing --fail-under=85
    - run: uv run python -m coverage xml -o coverage.xml
```

**Status Check**: Required for PR merge. If coverage drops below 85%, merge is blocked.

______________________________________________________________________

## References

- **Testing Guide**: `docs/03-guides/testing.md` — Full testing documentation
- **RULES.md**: Section on coverage requirements (≥85%)
- **GitHub Policy**: `docs/00-project/governance/05-github-policy.md` — CI checks
- **pyproject.toml**: Lines 203-229 for full configuration

______________________________________________________________________

## Changelog

| Date       | Change                                                       | Impact                                                                       |
| ---------- | ------------------------------------------------------------ | ---------------------------------------------------------------------------- |
| 2026-03-26 | Synced local and CI command examples with Makefile/tests.yml | Clarified serial default, split coverage flow, and resilient coverage-verify |
| 2026-03-08 | Added `@overload`, bare `pass`, ellipsis patterns            | P3 optimization: focus metrics on executable code                            |
| 2026-02-18 | Initial coverage config                                      | Baseline 85% threshold                                                       |

______________________________________________________________________

*Last synced: 2026-03-26 | Codex documentation audit*
