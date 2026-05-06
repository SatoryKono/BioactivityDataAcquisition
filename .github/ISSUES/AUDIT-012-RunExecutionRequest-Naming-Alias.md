# AUDIT-012: Canonicalize RunExecutionRequest naming and remove ambiguous context alias

## 1. Title
[refactor] Canonicalize RunExecutionRequest naming and remove ambiguous context alias

## 2. Problem
The CLI execution model has both RunExecutionContext and RunExecutionRequest. In the canonical module, RunExecutionRequest is an alias for RunExecutionContext; in a compatibility facade, RunExecutionContext aliases RunExecutionRequest. This creates two names for one application request model.

## 3. Evidence
- `src/bioetl/application/services/execution/cli_run_orchestration_models.py::RunExecutionContext` (line 64)
- `src/bioetl/application/services/execution/cli_run_orchestration_models.py::RunExecutionRequest` (line 88): `RunExecutionRequest = RunExecutionContext`
- `src/bioetl/application/services/cli_run_orchestration_models.py` (line 14): `RunExecutionContext = RunExecutionRequest`
- Import sites in: `cli_run_orchestration_service.py`, `cli_run_orchestration_contracts.py`, `execution/__init__.py`

## 4. Root Cause
Compatibility alias drift after refactoring the CLI execution seam.

## 5. Architectural Impact
- Layer boundaries: no boundary violation, but public application seam is ambiguous
- Dependency direction: unchanged
- Determinism / idempotency: no runtime data effect
- Testing: duplicate import paths increase test maintenance and stale assertions
- Governance: violates naming clarity for request/context models

## 6. Required Outcome
There must be exactly one canonical first-party model name for the prepared CLI execution request. Preferred canonical name: RunExecutionRequest.

RunExecutionContext must either be removed or retained only as a time-boxed compatibility alias with deprecation coverage.

## 7. File-level Implementation Plan
### Changes
- `src/bioetl/application/services/execution/cli_run_orchestration_models.py`
  - Rename class: `RunExecutionContext → RunExecutionRequest`
  - Update `RunPreparationResult.request` type: `RunExecutionRequest | None`
  - Remove canonical alias: `RunExecutionRequest = RunExecutionContext`
  - Update `__all__`
  - Keep RunExecutionContext only if required as deprecated alias:
    - add deprecation comment
    - add removal date
    - add test that first-party code does not import it

- `src/bioetl/application/services/execution/cli_run_orchestration_service.py`
  - Update imports and type hints to RunExecutionRequest

- `src/bioetl/application/services/cli_run_orchestration_models.py`
  - Keep facade export for backward compatibility only if existing external imports require it
  - Prefer: export RunExecutionRequest
  - Optionally expose RunExecutionContext as deprecated alias
  - Do not invert aliasing in multiple places

- `src/bioetl/application/services/cli_run_orchestration_service.py`
  - Update re-exports

- `src/bioetl/interfaces/cli/...`
  - Update any imports from RunExecutionContext to RunExecutionRequest

- `tests/...`
  - Update model import tests
  - Add regression test:
    - first-party source does not import RunExecutionContext
    - compatibility facade still resolves if retained
    - warning is emitted if deprecated alias is used

### Refactoring actions
- Remove duplicate naming
- Keep only one canonical model definition
- Do not change CLI execution behavior

### Contracts impact
- Application API naming cleanup
- No data schema impact
- No DQ contract impact

### Migration
- No data migration. Internal import migration only

## 8. Constraints
Forbidden:
- moving CLI orchestration into infrastructure
- adding test-only production branches
- introducing cyclic imports between application service facades
- weakening Gold strict validation
- changing Quarantine payload
- adding I/O to domain

## 9. Acceptance Criteria
- Canonical class is RunExecutionRequest
- First-party code imports only RunExecutionRequest
- RunExecutionContext is removed or explicitly deprecated with removal date
- Unit tests pass
- CLI command tests pass
- Mypy passes for changed modules
- Architecture tests pass
- Execution behavior is unchanged for valid CLI inputs

## 10. Priority
P2. Ambiguous model naming is not a system failure, but it does rot boundaries quietly.

## 11. Size
M. Import cleanup plus tests.

## 12. Labels
refactor, technical-debt, testing

## 13. Dependencies
None.
