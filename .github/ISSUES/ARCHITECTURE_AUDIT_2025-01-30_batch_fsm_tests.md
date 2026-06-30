# Issue: Exhaustive Batch FSM State Transition Tests

## Type
- [ ] Feature
- [ ] Bug
- [ ] Technical Debt
- [ ] Testing

## Priority
- [ ] P0 (Critical)
- [ ] P1 (High)
- [ ] P2 (Medium)
- [x] Low

## Context
Based on the architecture audit (2025-01-30), the project has strong test coverage but lacks exhaustive FSM transition tests for the Batch aggregate. Core domain logic should be bulletproof with comprehensive state machine validation.

## Problem
- Batch FSM state transitions are not exhaustively tested
- Current tests may miss edge cases
- Risk of invariant violations in runtime
- No explicit test matrix for all state transitions
- Missing tests for invalid transitions

## Impact
- Runtime invariant violations
- Data corruption risk
- Difficult to reason about domain logic
- Regression risk when modifying Batch FSM

## Proposed Solution

### Step 1: Document State Machine
Create explicit documentation of Batch FSM:
```
States: OPEN, SEALED, WRITING, COMMITTED, FAILED
Valid transitions:
- OPEN → SEALED (seal())
- SEALED → WRITING (begin_write())
- WRITING → COMMITTED (commit())
- WRITING → FAILED (fail())
Invalid transitions:
- COMMITTED → OPEN (should fail)
- FAILED → OPEN (should fail)
- SEALED → COMMITTED (should fail)
- etc.
```

### Step 2: Create Exhaustive Test Matrix
Create `tests/unit/domain/aggregates/test_batch_fsm_exhaustive.py`:
```python
@pytest.mark.parametrize("from_state,to_state,should_succeed", [
    # Valid transitions
    (BatchState.OPEN, BatchState.SEALED, True),
    (BatchState.SEALED, BatchState.WRITING, True),
    (BatchState.WRITING, BatchState.COMMITTED, True),
    (BatchState.WRITING, BatchState.FAILED, True),
    
    # Invalid transitions
    (BatchState.COMMITTED, BatchState.OPEN, False),
    (BatchState.FAILED, BatchState.OPEN, False),
    (BatchState.SEALED, BatchState.COMMITTED, False),
    (BatchState.OPEN, BatchState.COMMITTED, False),
    # ... all combinations
])
def test_batch_state_transitions_exhaustive(from_state, to_state, should_succeed):
    batch = Batch(...)
    batch.state = from_state
    
    if should_succeed:
        batch.transition_to(to_state)
        assert batch.state == to_state
    else:
        with pytest.raises(InvalidStateTransitionError):
            batch.transition_to(to_state)
```

### Step 3: Add Invariant Tests
Test invariants for each state:
- OPEN: No invariants
- SEALED: content_hash immutable, no records can be added
- WRITING: content_hash immutable, records can be added
- COMMITTED: Immutable, no changes allowed
- FAILED: Immutable, no changes allowed

## Implementation Steps
1. Document Batch FSM in code comments or docstring
2. Create test matrix file
3. Implement exhaustive transition tests
4. Implement invariant tests for each state
5. Add to CI test suite
6. Verify coverage reaches 100% for batch.py

## Acceptance Criteria
- [ ] Test file `tests/unit/domain/aggregates/test_batch_fsm_exhaustive.py` created
- [ ] All state transition combinations tested
- [ ] All invalid transitions raise appropriate errors
- [ ] All invariants tested for each state
- [ ] Coverage for `src/bioetl/domain/aggregates/batch.py` = 100%
- [ ] Tests pass in CI
- [ ] Documentation updated

## Evidence
- Architecture audit score: DDD Alignment 7.0/10
- Source file: `src/bioetl/domain/aggregates/batch.py`
- Current tests: `tests/unit/domain/aggregates/test_batch.py`

## Related Issues
- Architecture audit 2025-01-30
- Aggregate invariants documentation
- DDD alignment improvement

## Labels
`testing`, `ddd`, `domain`, `quality`, `coverage`

## Estimate
8 hours
