# AUDIT-013: Remove composite runtime dependency alias drift

## 1. Title
[refactor] Remove composite runtime dependency alias drift

## 2. Problem
Composite runtime models retain a compatibility alias for the dependency container type. This alias obscures the canonical model name used by CompositePipelineRunner orchestration.

## 3. Evidence
- `src/bioetl/application/composite/runtime_models.py::CompositeRunnerDependencyGroup` (line 92)
- `src/bioetl/application/composite/runtime_models.py::CompositeRunnerDependencies` (line 119): `CompositeRunnerDependencies = CompositeRunnerDependencyGroup`

Note: The finalization.py aliases mentioned in the original issue (CompositePipelineFinalizationContext/Request, CompositeResultBuildContext/Request) do not exist in the current codebase.

## 4. Root Cause
Legacy compatibility shim was retained after composite runner decomposition without a sunset plan.

## 5. Architectural Impact
- Layer boundaries: no immediate violation
- Dependency direction: no direct issue, but import surfaces become harder to govern
- Composite Pipeline Pattern: unclear canonical naming makes ADR-026 orchestration harder to audit
- Testing: duplicate aliases increase import-path coverage noise
- Governance: weakens suffix consistency for Request versus Context

## 6. Required Outcome
Composite application code must expose one canonical name for the dependency container model.

Selected canonical name: CompositeRunnerDependencies (rename class and remove alias).

The selected canonical name must be used across first-party code. Deprecated aliases, if kept, must have explicit removal metadata and tests.

## 7. File-level Implementation Plan
### Changes
- `src/bioetl/application/composite/runtime_models.py`
  - Rename class: `CompositeRunnerDependencyGroup → CompositeRunnerDependencies`
  - Remove alias: `CompositeRunnerDependencies = CompositeRunnerDependencyGroup`
  - Update `__all__`

- `src/bioetl/application/composite/runtime_wiring_api.py`
  - Update imports to canonical dependency container name

- `src/bioetl/application/composite/runner_pkg/...`
  - Update all references: `CompositeRunnerDependencyGroup → CompositeRunnerDependencies`

- `tests/unit/application/composite/...`
  - Update imports and constructor names
  - Add no-first-party-alias-import test for composite runtime models

### Refactoring actions
- Remove alias drift
- Avoid moving composite orchestration into domain
- Avoid introducing new DTOs with identical fields

### Contracts impact
- Application internal API cleanup
- No Gold/Silver schema impact
- No DQ rule impact
- No config contract change

### Migration
- No data migration. If external imports exist, keep compatibility aliases behind deprecation warning and removal date

## 8. Constraints
Forbidden:
- importing infrastructure into domain
- adding I/O to domain
- changing composite execution order
- changing merge semantics
- changing Quarantine payload
- weakening Gold strict validation
- creating cyclic dependencies

## 9. Acceptance Criteria
- First-party application code uses one canonical name for CompositeRunnerDependencies
- Alias assignment is removed or deprecated with explicit removal date
- Unit tests pass
- Composite pipeline tests pass
- Architecture tests pass
- No new dependency cycles
- Composite output remains deterministic for the same input fixtures

## 10. Priority
P2. Naming drift in composite orchestration is not catastrophic, but it makes ADR-026 enforcement harder than it needs to be.

## 11. Size
M. Several imports and tests, no execution rewrite.

## 12. Labels
refactor, technical-debt, architecture

## 13. Dependencies
Depends on Issue 12 only if both are done in one PR to standardize request naming conventions together. Otherwise independent.
