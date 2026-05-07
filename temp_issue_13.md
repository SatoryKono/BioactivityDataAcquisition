## Problem

Composite runtime models retain compatibility aliases for request/dependency types. These aliases obscure the canonical model names used by CompositePipelineRunner orchestration.

## Evidence

- `src/bioetl/application/composite/runner_pkg/runner_completion_helpers.py:182` - `CompositePipelineFinalizationRequest = CompositePipelineFinalizationContext`
- `src/bioetl/application/composite/runner_pkg/runner_result_types.py:41` - `CompositeResultBuildRequest = CompositeResultBuildContext`

## Root Cause

Legacy compatibility shims were retained after composite runner decomposition without a sunset plan.

## Architectural Impact

- Layer boundaries: No immediate violation
- Dependency direction: Import surfaces become harder to govern
- Composite Pipeline Pattern: Unclear canonical naming makes ADR-026 orchestration harder to audit
- Testing: Duplicate aliases increase import-path coverage noise
- Governance: Weakens suffix consistency for Request versus Context

## Required Outcome

Composite application code must expose one canonical name for each model role:
- Finalization input: `CompositePipelineFinalizationRequest`
- Result build input: `CompositeResultBuildRequest`

The selected canonical names must be used across first-party code. Deprecated aliases, if kept, must have explicit removal metadata and tests.

## Implementation Plan

1. In `runner_completion_helpers.py`:
   - Rename class `CompositePipelineFinalizationContext` → `CompositePipelineFinalizationRequest`
   - Remove alias `CompositePipelineFinalizationRequest = CompositePipelineFinalizationContext`
   - Update function signature: `finalize_pipeline(host, request: CompositePipelineFinalizationRequest)`
   - Update docstrings

2. In `runner_result_types.py`:
   - Rename class `CompositeResultBuildContext` → `CompositeResultBuildRequest`
   - Remove alias `CompositeResultBuildRequest = CompositeResultBuildContext`
   - Update docstrings

3. Update all references across composite runner package

4. Add no-first-party-alias-import test for composite runtime models

## Acceptance Criteria

- First-party application code uses one canonical name for each composite runtime model
- Alias assignments are removed or deprecated with explicit removal date
- Unit tests pass
- Composite pipeline tests pass
- Architecture tests pass
- No new dependency cycles
- Composite output remains deterministic for the same input fixtures

## Priority

P2 - Naming drift in composite orchestration is not catastrophic, but it makes ADR-026 enforcement harder

## Size

M - Several imports and tests, no execution rewrite

## Labels

refactor, technical-debt, architecture
