## Problem

The CLI execution model has both `RunExecutionRequest` and `RunExecutionSpec`. In the canonical module (`src/bioetl/application/services/execution/cli_run_orchestration_models.py`), `RunExecutionRequest` is an alias for `RunExecutionSpec`. In the compatibility facade (`src/bioetl/application/services/cli_run_orchestration_models.py`), `RunExecutionContext` is deprecated with removal date 2026-09-30.

The canonical class should be `RunExecutionRequest`, not `RunExecutionSpec` with an alias.

## Evidence

- `src/bioetl/application/services/execution/cli_run_orchestration_models.py:73` - `RunExecutionRequest = RunExecutionSpec`
- `src/bioetl/application/services/cli_run_orchestration_models.py:15` - `_RUN_EXECUTION_CONTEXT_REMOVAL_DATE = "2026-09-30"`
- `src/bioetl/application/services/cli_run_orchestration_models.py:27-37` - Deprecation warning for `RunExecutionContext`

## Root Cause

Compatibility alias drift after refactoring the CLI execution seam. The alias direction is inverted - canonical should be the desired name, not an alias.

## Architectural Impact

- Layer boundaries: No boundary violation, but public application seam is ambiguous
- Testing: Duplicate import paths increase test maintenance
- Governance: Violates naming clarity for request/context models

## Required Outcome

There must be exactly one canonical first-party model name: `RunExecutionRequest`. Rename `RunExecutionSpec` to `RunExecutionRequest` and remove the alias.

## Implementation Plan

1. Rename class `RunExecutionSpec` → `RunExecutionRequest` in `cli_run_orchestration_models.py`
2. Remove alias `RunExecutionRequest = RunExecutionSpec`
3. Update all imports and type hints across the codebase
4. Keep `RunExecutionContext` deprecated alias in facade with removal date 2026-09-30
5. Add test that first-party code does not import `RunExecutionContext`

## Acceptance Criteria

- Canonical class is `RunExecutionRequest`
- First-party code imports only `RunExecutionRequest`
- `RunExecutionContext` is explicitly deprecated with removal date
- Unit tests pass
- CLI command tests pass
- Mypy passes
- Execution behavior unchanged

## Priority

P2 - Naming clarity, not a production outage

## Size

M - Import cleanup plus tests

## Labels

refactor, technical-debt, testing
