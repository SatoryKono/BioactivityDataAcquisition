# Issue: Document Aggregate Invariants

## Type
- [ ] Feature
- [ ] Bug
- [ ] Technical Debt
- [ ] Documentation

## Priority
- [ ] P0 (Critical)
- [ ] P1 (High)
- [x] P2 (Medium)
- [ ] Low

## Context
Based on the architecture audit (2025-01-30), the project has strong DDD alignment but lacks canonical documentation for aggregate invariants. This makes reasoning about domain logic difficult and increases onboarding complexity.

## Problem
- Aggregate invariants are not documented in `docs/02-architecture/domain/aggregate-invariants.md`
- Core domain logic (Batch FSM, PipelineRun, QuarantineEntry) has implicit rules that are not explicitly documented
- New team members must read source code to understand domain rules
- Risk of invariant violations increases without explicit documentation

## Impact
- Onboarding complexity
- Reasoning difficulty about domain logic
- Risk of invariant violations in runtime
- Knowledge silos

## Proposed Solution
Create `docs/02-architecture/domain/aggregate-invariants.md` with canonical documentation for:

### Batch Aggregate
1. State transition: OPEN → SEALED → WRITING → COMMITTED/FAILED (one-way)
2. content_hash immutable after SEALED
3. records cannot be added after SEALED
4. validation rules for each state transition
5. error handling for invalid transitions

### PipelineRun Aggregate
1. State machine states and transitions
2. Completion conditions
3. Failure handling rules
4. Retry policies
5. Cancellation semantics

### QuarantineEntry Aggregate
1. Creation conditions
2. Resolution rules
3. Lifecycle states
4. Metadata invariants

## Implementation Steps
1. Create `docs/02-architecture/domain/aggregate-invariants.md`
2. Document all invariants for each aggregate
3. Add diagrams for state machines (Mermaid)
4. Add examples of valid/invalid state transitions
5. Link from `docs/02-architecture/01-domain-layer.md`
6. Add to README.md under Architecture section

## Acceptance Criteria
- [ ] File `docs/02-architecture/domain/aggregate-invariants.md` exists
- [ ] All three aggregates documented
- [ ] State machine diagrams included (Mermaid)
- [ ] Transition rules explicitly stated
- [ ] Examples provided for each invariant
- [ ] Linked from domain-layer documentation
- [ ] Linked from README.md

## Evidence
- Architecture audit score: DDD Alignment 7.0/10
- Missing documentation: `docs/02-architecture/domain/aggregate-invariants.md`
- Source files:
  - `src/bioetl/domain/aggregates/batch.py`
  - `src/bioetl/domain/aggregates/pipeline_run.py`
  - `src/bioetl/domain/aggregates/quarantine_entry.py`

## Related Issues
- Architecture audit 2025-01-30
- DDD alignment improvement

## Labels
`documentation`, `architecture`, `ddd`, `technical-debt`

## Estimate
4 hours
