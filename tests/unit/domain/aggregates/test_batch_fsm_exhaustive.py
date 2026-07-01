"""Exhaustive Batch FSM State Transition Tests.

This module provides comprehensive state machine validation for the Batch aggregate.
All state transition combinations are tested to ensure:
1. Valid transitions succeed
2. Invalid transitions raise InvalidStateError
3. Invariants are preserved for each state
4. Domain events are emitted correctly

State Machine:
    OPEN → SEALED → WRITING → COMMITTED
                         → FAILED

Valid transitions:
- OPEN → SEALED (seal())
- SEALED → WRITING (mark_writing())
- WRITING → COMMITTED (mark_committed())
- WRITING → FAILED (mark_failed())

Invalid transitions:
- All other combinations raise InvalidStateError
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from bioetl.domain.aggregates.batch import Batch, BatchStatus
from bioetl.domain.exceptions import InvalidStateError
from bioetl.domain.types import RunID
from tests.helpers.deterministic_ids import deterministic_uuid_value

pytestmark = pytest.mark.unit


def _ts(offset_seconds: int = 0) -> datetime:
    """Return deterministic UTC timestamps for batch tests."""
    return datetime(2026, 1, 1, tzinfo=UTC)


@pytest.fixture
def run_id() -> RunID:
    """Create a test run ID."""
    return RunID(deterministic_uuid_value("unit.batch.run_id"))


@pytest.fixture
def open_batch(run_id: RunID) -> Batch:
    """Create a test batch in OPEN state."""
    return Batch.create(run_id=run_id, created_at=_ts(0))


@pytest.fixture
def sealed_batch(run_id: RunID) -> Batch:
    """Create a test batch in SEALED state."""
    batch = Batch.create(run_id=run_id, created_at=_ts(0))
    batch.seal(sealed_at=_ts(1))
    return batch


@pytest.fixture
def writing_batch(run_id: RunID) -> Batch:
    """Create a test batch in WRITING state."""
    batch = Batch.create(run_id=run_id, created_at=_ts(0))
    batch.seal(sealed_at=_ts(1))
    batch.mark_writing()
    return batch


# ──────────────────────────────────────────────────────────────────────────────
# Exhaustive State Transition Matrix
# ──────────────────────────────────────────────────────────────────────────────

# All possible state pairs (from_state, to_state)
ALL_STATES = [
    BatchStatus.OPEN,
    BatchStatus.SEALED,
    BatchStatus.WRITING,
    BatchStatus.COMMITTED,
    BatchStatus.FAILED,
]

# Valid transitions with their methods
VALID_TRANSITIONS = [
    (BatchStatus.OPEN, BatchStatus.SEALED, "seal"),
    (BatchStatus.SEALED, BatchStatus.WRITING, "mark_writing"),
    (BatchStatus.WRITING, BatchStatus.COMMITTED, "mark_committed"),
    (BatchStatus.WRITING, BatchStatus.FAILED, "mark_failed"),
]

# Generate all invalid transitions (excluding self-transitions)
INVALID_TRANSITIONS = [
    (from_state, to_state)
    for from_state in ALL_STATES
    for to_state in ALL_STATES
    if from_state != to_state  # Exclude self-transitions
    and (from_state, to_state) not in [(f, t) for f, t, _ in VALID_TRANSITIONS]
]


@pytest.mark.parametrize("from_state,to_state,method", VALID_TRANSITIONS)
def test_valid_state_transitions_succeed(
    from_state: BatchStatus,
    to_state: BatchStatus,
    method: str,
    run_id: RunID,
) -> None:
    """Test that all valid state transitions succeed."""
    batch = Batch.create(run_id=run_id, created_at=_ts(0))

    # Set initial state
    if from_state == BatchStatus.OPEN:
        assert batch.status == BatchStatus.OPEN
    elif from_state == BatchStatus.SEALED:
        batch.seal(sealed_at=_ts(1))
        assert batch.status == BatchStatus.SEALED
    elif from_state == BatchStatus.WRITING:
        batch.seal(sealed_at=_ts(1))
        batch.mark_writing()
        assert batch.status == BatchStatus.WRITING
    else:
        pytest.fail(f"Invalid initial state for valid transition: {from_state}")

    # Perform transition
    if method == "seal":
        batch.seal(sealed_at=_ts(2))
    elif method == "mark_writing":
        batch.mark_writing()
    elif method == "mark_committed":
        batch.mark_committed(
            layer="bronze",
            committed_at=_ts(3),
        )
    elif method == "mark_failed":
        batch.mark_failed(
            layer="bronze",
            error="Test error",
            failed_at=_ts(3),
        )
    else:
        pytest.fail(f"Unknown method: {method}")

    # Verify state transition
    assert batch.status == to_state


@pytest.mark.parametrize("from_state,to_state", INVALID_TRANSITIONS)
def test_invalid_state_transitions_raise_error(
    from_state: BatchStatus,
    to_state: BatchStatus,
    run_id: RunID,
) -> None:
    """Test that all invalid state transitions raise InvalidStateError."""
    # Skip transitions to OPEN (initial state has no transition method)
    if to_state == BatchStatus.OPEN:
        pytest.skip("OPEN is initial state, no transition method to it")

    batch = Batch.create(run_id=run_id, created_at=_ts(0))

    # Set initial state
    if from_state == BatchStatus.OPEN:
        assert batch.status == BatchStatus.OPEN
    elif from_state == BatchStatus.SEALED:
        batch.seal(sealed_at=_ts(1))
        assert batch.status == BatchStatus.SEALED
    elif from_state == BatchStatus.WRITING:
        batch.seal(sealed_at=_ts(1))
        batch.mark_writing()
        assert batch.status == BatchStatus.WRITING
    elif from_state == BatchStatus.COMMITTED:
        batch.seal(sealed_at=_ts(1))
        batch.mark_writing()
        batch.mark_committed(
            layer="bronze",
            committed_at=_ts(3),
        )
        assert batch.status == BatchStatus.COMMITTED
    elif from_state == BatchStatus.FAILED:
        batch.seal(sealed_at=_ts(1))
        batch.mark_writing()
        batch.mark_failed(
            layer="bronze",
            error="Test error",
            failed_at=_ts(3),
        )
        assert batch.status == BatchStatus.FAILED
    else:
        pytest.fail(f"Unknown initial state: {from_state}")

    # Attempt invalid transition
    with pytest.raises(InvalidStateError) as exc_info:
        if to_state == BatchStatus.SEALED:
            batch.seal(sealed_at=_ts(2))
        elif to_state == BatchStatus.WRITING:
            batch.mark_writing()
        elif to_state == BatchStatus.COMMITTED:
            batch.mark_committed(
                layer="bronze",
                committed_at=_ts(3),
            )
        elif to_state == BatchStatus.FAILED:
            batch.mark_failed(
                layer="bronze",
                error="Test error",
                failed_at=_ts(3),
            )
        else:
            pytest.fail(f"Unknown target state: {to_state}")

    # Verify error contains current state and attempted operation
    error_message = str(exc_info.value)
    assert from_state.value in error_message or str(from_state) in error_message


# ──────────────────────────────────────────────────────────────────────────────
# State Invariant Tests
# ──────────────────────────────────────────────────────────────────────────────

def test_open_state_invariants(open_batch: Batch) -> None:
    """Test invariants for OPEN state."""
    assert open_batch.status == BatchStatus.OPEN
    assert open_batch.status.is_modifiable()
    assert open_batch.sealed_at is None


def test_sealed_state_invariants(sealed_batch: Batch) -> None:
    """Test invariants for SEALED state."""
    assert sealed_batch.status == BatchStatus.SEALED
    assert not sealed_batch.status.is_modifiable()
    assert sealed_batch.sealed_at is not None

    # Cannot add records after sealing
    with pytest.raises(InvalidStateError):
        sealed_batch.add_records([])


def test_writing_state_invariants(writing_batch: Batch) -> None:
    """Test invariants for WRITING state."""
    assert writing_batch.status == BatchStatus.WRITING
    assert not writing_batch.status.is_modifiable()
    assert writing_batch.sealed_at is not None


def test_committed_state_invariants(run_id: RunID) -> None:
    """Test invariants for COMMITTED state."""
    batch = Batch.create(run_id=run_id, created_at=_ts(0))
    batch.seal(sealed_at=_ts(1))
    batch.mark_writing()
    batch.mark_committed(
        layer="bronze",
        committed_at=_ts(3),
    )

    assert batch.status == BatchStatus.COMMITTED
    assert not batch.status.is_modifiable()
    assert batch.sealed_at is not None

    # Cannot transition from COMMITTED
    with pytest.raises(InvalidStateError):
        batch.mark_writing()


def test_failed_state_invariants(run_id: RunID) -> None:
    """Test invariants for FAILED state."""
    batch = Batch.create(run_id=run_id, created_at=_ts(0))
    batch.seal(sealed_at=_ts(1))
    batch.mark_writing()
    batch.mark_failed(
        layer="bronze",
        error="Test error",
        failed_at=_ts(3),
    )

    assert batch.status == BatchStatus.FAILED
    assert not batch.status.is_modifiable()
    assert batch.sealed_at is not None

    # Cannot transition from FAILED
    with pytest.raises(InvalidStateError):
        batch.mark_writing()


# ──────────────────────────────────────────────────────────────────────────────
# Domain Event Emission Tests
# ──────────────────────────────────────────────────────────────────────────────

def test_seal_emits_batch_sealed_event(sealed_batch: Batch) -> None:
    """Test that seal() emits BatchSealed event."""
    events = sealed_batch.collect_events()
    assert len(events) == 2  # BatchCreated + BatchSealed

    sealed_event = events[1]
    assert type(sealed_event).__name__ == "BatchSealed"
    assert sealed_event.batch_id == sealed_batch.batch_id


def test_mark_committed_emits_batch_written_event(run_id: RunID) -> None:
    """Test that mark_committed() emits BatchWritten event."""
    batch = Batch.create(run_id=run_id, created_at=_ts(0))
    batch.seal(sealed_at=_ts(1))
    batch.mark_writing()
    batch.mark_committed(
        layer="bronze",
        committed_at=_ts(3),
    )

    events = batch.collect_events()
    assert len(events) == 3  # BatchCreated + BatchSealed + BatchWritten

    written_event = events[2]
    assert type(written_event).__name__ == "BatchWritten"
    assert written_event.batch_id == batch.batch_id


def test_mark_failed_emits_batch_failed_event(run_id: RunID) -> None:
    """Test that mark_failed() emits BatchFailed event."""
    batch = Batch.create(run_id=run_id, created_at=_ts(0))
    batch.seal(sealed_at=_ts(1))
    batch.mark_writing()
    batch.mark_failed(
        layer="bronze",
        error="Test error",
        failed_at=_ts(3),
    )

    events = batch.collect_events()
    assert len(events) == 3  # BatchCreated + BatchSealed + BatchFailed

    failed_event = events[2]
    assert type(failed_event).__name__ == "BatchFailed"
    assert failed_event.batch_id == batch.batch_id


# ──────────────────────────────────────────────────────────────────────────────
# Edge Case Tests
# ──────────────────────────────────────────────────────────────────────────────

def test_cannot_seal_already_sealed_batch(sealed_batch: Batch) -> None:
    """Test that sealing an already sealed batch raises error."""
    with pytest.raises(InvalidStateError) as exc_info:
        sealed_batch.seal(sealed_at=_ts(2))

    assert "Cannot seal" in str(exc_info.value)


def test_cannot_mark_writing_from_open_state(open_batch: Batch) -> None:
    """Test that marking writing from OPEN state raises error."""
    with pytest.raises(InvalidStateError) as exc_info:
        open_batch.mark_writing()

    assert "Cannot mark as writing" in str(exc_info.value)


def test_cannot_mark_committed_from_sealed_state(sealed_batch: Batch) -> None:
    """Test that committing from SEALED state raises error."""
    with pytest.raises(InvalidStateError) as exc_info:
        sealed_batch.mark_committed(
            layer="bronze",
            committed_at=_ts(3),
        )

    assert "Cannot commit" in str(exc_info.value)


def test_cannot_mark_failed_from_sealed_state(sealed_batch: Batch) -> None:
    """Test that failing from SEALED state raises error."""
    with pytest.raises(InvalidStateError) as exc_info:
        sealed_batch.mark_failed(
            layer="bronze",
            error="Test error",
            failed_at=_ts(3),
        )

    assert "Cannot fail" in str(exc_info.value)


def test_cannot_transition_from_committed_to_failed(run_id: RunID) -> None:
    """Test that transitioning from COMMITTED to FAILED raises error."""
    batch = Batch.create(run_id=run_id, created_at=_ts(0))
    batch.seal(sealed_at=_ts(1))
    batch.mark_writing()
    batch.mark_committed(
        layer="bronze",
        committed_at=_ts(3),
    )

    with pytest.raises(InvalidStateError) as exc_info:
        batch.mark_failed(
            layer="bronze",
            error="Test error",
            failed_at=_ts(4),
        )

    assert "Cannot fail" in str(exc_info.value)


def test_cannot_transition_from_failed_to_committed(run_id: RunID) -> None:
    """Test that transitioning from FAILED to COMMITTED raises error."""
    batch = Batch.create(run_id=run_id, created_at=_ts(0))
    batch.seal(sealed_at=_ts(1))
    batch.mark_writing()
    batch.mark_failed(
        layer="bronze",
        error="Test error",
        failed_at=_ts(3),
    )

    with pytest.raises(InvalidStateError) as exc_info:
        batch.mark_committed(
            layer="bronze",
            committed_at=_ts(4),
        )

    assert "Cannot commit" in str(exc_info.value)


# ──────────────────────────────────────────────────────────────────────────────
# Property Coverage Tests (for 100% coverage)
# ──────────────────────────────────────────────────────────────────────────────

def test_batch_properties_coverage(open_batch: Batch) -> None:
    """Test all Batch properties for coverage."""
    # Test all properties that are in _BatchReadModelMixin
    assert open_batch.batch_id is not None
    assert open_batch.run_id is not None
    assert open_batch.status == BatchStatus.OPEN
    assert open_batch.records == ()
    assert open_batch.all_records == ()
    assert open_batch.quarantined_records == ()
    assert open_batch.record_count == 0
    assert open_batch.valid_count == 0
    assert open_batch.quarantined_count == 0
    assert open_batch.next_index == 0
    assert open_batch.created_at == _ts(0)
    assert open_batch.sealed_at is None
    assert open_batch.metadata == {}

    # Test __repr__
    repr_str = repr(open_batch)
    assert "Batch(" in repr_str
    assert "status='open'" in repr_str


def test_seal_with_counts_coverage(run_id: RunID) -> None:
    """Test seal_with_counts method for coverage."""
    batch = Batch.create(run_id=run_id, created_at=_ts(0))
    batch.seal_with_counts(
        record_count=10,
        valid_count=8,
        quarantined_count=2,
        sealed_at=_ts(1),
    )
    assert batch.status == BatchStatus.SEALED
    assert batch.sealed_at == _ts(1)


def test_quarantine_record_coverage(run_id: RunID) -> None:
    """Test quarantine_record method for coverage."""
    batch = Batch.create(run_id=run_id, created_at=_ts(0))
    record = batch.add_record({"test": "data"}, entity_id="test-entity")
    
    quarantined = batch.quarantine_record(
        record=record,
        error="Test error",
        error_code="TEST_ERROR",
        quarantined_at=_ts(1),
    )
    
    assert not quarantined.is_valid
    assert batch.quarantined_count == 1


def test_collect_events_coverage(run_id: RunID) -> None:
    """Test collect_events method for coverage."""
    batch = Batch.create(run_id=run_id, created_at=_ts(0))
    batch.seal(sealed_at=_ts(1))
    
    events = batch.collect_events()
    assert len(events) == 2  # BatchCreated + BatchSealed
    
    # Events should be cleared after collection
    events2 = batch.collect_events()
    assert len(events2) == 0
