"""Tests for Batch aggregate invariants.

Tests verify that:
1. All records in a batch have the same batch_id
2. Records cannot be added after the batch is sealed
3. batch_id is unique and immutable
4. Record indices are sequential starting from start_index
5. Quarantined records are tracked separately
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from bioetl.domain.aggregates.batch import (
    Batch,
    BatchRecord,
    BatchStatus,
)
from bioetl.domain.exceptions import InvalidStateError
from bioetl.domain.types import BatchID, ContentHash, EntityID, RunID
from tests.helpers.deterministic_ids import deterministic_uuid_value

pytestmark = pytest.mark.unit


def _ts(offset_seconds: int = 0) -> datetime:
    """Return deterministic UTC timestamps for batch tests."""
    return datetime(2026, 1, 1, tzinfo=UTC) + timedelta(seconds=offset_seconds)


@pytest.fixture
def run_id() -> RunID:
    """Create a test run ID."""
    return RunID(deterministic_uuid_value("unit.batch.run_id"))


@pytest.fixture
def batch(run_id: RunID) -> Batch:
    """Create a test batch."""
    return Batch.create(run_id=run_id, created_at=_ts(0))


# ──────────────────────────────────────────────────────────────────────────────
# BatchRecord Value Object Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestBatchRecordInvariants:
    """Tests for BatchRecord value object invariants."""

    def test_index_cannot_be_negative(self) -> None:
        """Invariant: record index >= 0."""
        with pytest.raises(ValueError, match="cannot be negative"):
            BatchRecord(
                index=-1,
                entity_id=None,
                content_hash=None,
                data={"id": "1"},
            )

    def test_invalid_record_must_have_error(self) -> None:
        """Invariant: invalid record requires error message."""
        with pytest.raises(ValueError, match="must have an error"):
            BatchRecord(
                index=0,
                entity_id=None,
                content_hash=None,
                data={"id": "1"},
                is_valid=False,
                error=None,
            )

    def test_valid_record_creation(self) -> None:
        """Valid BatchRecord should be created successfully."""
        record = BatchRecord(
            index=0,
            entity_id=EntityID("test:1"),
            content_hash=ContentHash("abc123"),
            data={"id": "1", "value": 100},
        )
        assert record.index == 0
        assert record.is_valid
        assert record.entity_id == EntityID("test:1")

    def test_batch_record_is_immutable(self) -> None:
        """BatchRecord should be frozen (immutable)."""
        record = BatchRecord(
            index=0,
            entity_id=None,
            content_hash=None,
            data={"id": "1"},
        )
        with pytest.raises(AttributeError):
            record.index = 1  # type: ignore

    def test_with_validation_error_creates_invalid_copy(self) -> None:
        """with_validation_error() should create invalid copy."""
        record = BatchRecord(
            index=0,
            entity_id=EntityID("test:1"),
            content_hash=ContentHash("abc123"),
            data={"id": "1"},
        )

        invalid = record.with_validation_error("Test error", "SCHEMA_VIOLATION")

        # Original should be unchanged
        assert record.is_valid
        # New copy should be invalid
        assert not invalid.is_valid
        assert invalid.error == "Test error"
        assert invalid.error_code == "SCHEMA_VIOLATION"
        # Other fields preserved
        assert invalid.index == record.index
        assert invalid.entity_id == record.entity_id


# ──────────────────────────────────────────────────────────────────────────────
# Batch State Transition Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestBatchStateTransitions:
    """Tests for Batch state machine transitions."""

    def test_initial_status_is_open(self, batch: Batch) -> None:
        """New batch should be in OPEN status."""
        assert batch.status == BatchStatus.OPEN
        assert batch.sealed_at is None

    def test_seal_transitions_to_sealed(self, batch: Batch) -> None:
        """seal() should transition OPEN -> SEALED."""
        batch.add_record({"id": "1"})
        batch.seal(_ts(10))

        assert batch.status == BatchStatus.SEALED
        assert batch.sealed_at == _ts(10)

    def test_cannot_seal_already_sealed(self, batch: Batch) -> None:
        """Invariant: Cannot seal an already sealed batch."""
        batch.add_record({"id": "1"})
        batch.seal(_ts(10))

        with pytest.raises(InvalidStateError, match="Cannot seal"):
            batch.seal(_ts(11))

    def test_writing_to_committed_transitions(self, batch: Batch) -> None:
        """Test SEALED -> WRITING -> COMMITTED transitions."""
        batch.add_record({"id": "1"})
        batch.seal(_ts(10))
        batch.mark_writing()
        assert batch.status == BatchStatus.WRITING

        batch.mark_committed("silver", _ts(20))
        assert batch.status == BatchStatus.COMMITTED

    def test_writing_to_failed_transitions(self, batch: Batch) -> None:
        """Test SEALED -> WRITING -> FAILED transitions."""
        batch.add_record({"id": "1"})
        batch.seal(_ts(10))
        batch.mark_writing()

        batch.mark_failed("silver", "Write error", failed_at=_ts(20))
        assert batch.status == BatchStatus.FAILED


# ──────────────────────────────────────────────────────────────────────────────
# Record Management Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestBatchRecordManagement:
    """Tests for record addition and tracking."""

    def test_add_record(self, batch: Batch) -> None:
        """Should add record to batch."""
        record = batch.add_record({"id": "1", "value": 100})

        assert len(batch.all_records) == 1
        assert record.index == 0
        assert record.data == {"id": "1", "value": 100}

    def test_add_records_maintains_sequential_indices(self, batch: Batch) -> None:
        """Invariant: Record indices are sequential."""
        batch.add_record({"id": "1"})
        batch.add_record({"id": "2"})
        batch.add_record({"id": "3"})

        records = batch.all_records
        assert [r.index for r in records] == [0, 1, 2]

    def test_add_records_respects_start_index(self, run_id: RunID) -> None:
        """Invariant: Indices start from start_index."""
        batch = Batch.create(run_id=run_id, start_index=100, created_at=_ts(0))
        batch.add_record({"id": "1"})
        batch.add_record({"id": "2"})

        records = batch.all_records
        assert [r.index for r in records] == [100, 101]

    def test_cannot_add_record_after_seal(self, batch: Batch) -> None:
        """Invariant: Cannot add records after sealing."""
        batch.add_record({"id": "1"})
        batch.seal(_ts(10))

        with pytest.raises(InvalidStateError, match="Cannot add_record"):
            batch.add_record({"id": "2"})

    def test_add_multiple_records(self, batch: Batch) -> None:
        """Should add multiple records at once."""
        records = batch.add_records(
            [
                {"id": "1"},
                {"id": "2"},
                {"id": "3"},
            ]
        )

        assert len(records) == 3
        assert batch.record_count == 3


# ──────────────────────────────────────────────────────────────────────────────
# Quarantine Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestBatchQuarantine:
    """Tests for quarantine functionality."""

    def test_quarantine_record(self, batch: Batch) -> None:
        """Should mark record as quarantined."""
        record = batch.add_record({"id": "1"})
        quarantined = batch.quarantine_record(
            record,
            "Schema violation",
            "SCHEMA_VIOLATION",
            quarantined_at=_ts(10),
        )

        assert not quarantined.is_valid
        assert quarantined.error == "Schema violation"
        assert batch.quarantined_count == 1

    def test_quarantined_records_tracked_separately(self, batch: Batch) -> None:
        """Invariant: Quarantined records tracked separately."""
        record1 = batch.add_record({"id": "1"})
        batch.add_record({"id": "2"})
        batch.quarantine_record(record1, "Error", "ERR", quarantined_at=_ts(10))

        assert batch.record_count == 2  # Total
        assert batch.valid_count == 1  # Only valid
        assert batch.quarantined_count == 1

    def test_cannot_quarantine_after_seal(self, batch: Batch) -> None:
        """Invariant: Cannot quarantine after sealing."""
        record = batch.add_record({"id": "1"})
        batch.seal(_ts(10))

        with pytest.raises(InvalidStateError, match="Cannot quarantine"):
            batch.quarantine_record(record, "Error", "ERR", quarantined_at=_ts(11))

    def test_cannot_quarantine_foreign_record(
        self, batch: Batch, run_id: RunID
    ) -> None:
        """Invariant: Cannot quarantine record from another batch."""
        other_batch = Batch.create(run_id=run_id, created_at=_ts(1))
        foreign_record = other_batch.add_record({"id": "1"})

        batch.add_record({"id": "2"})

        with pytest.raises(ValueError, match="does not belong"):
            batch.quarantine_record(
                foreign_record,
                "Error",
                "ERR",
                quarantined_at=_ts(10),
            )


# ──────────────────────────────────────────────────────────────────────────────
# Encapsulation Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestBatchEncapsulation:
    """Tests for field encapsulation."""

    def test_batch_id_is_immutable(self, batch: Batch) -> None:
        """Invariant: batch_id cannot be changed."""
        original_id = batch.batch_id

        with pytest.raises(AttributeError):
            batch.batch_id = BatchID(deterministic_uuid_value("unit.batch.mutability"))  # type: ignore

        assert batch.batch_id == original_id

    def test_status_cannot_be_modified_externally(self, batch: Batch) -> None:
        """Invariant: status changes only through aggregate methods."""
        with pytest.raises(AttributeError):
            batch.status = BatchStatus.SEALED  # type: ignore

    def test_records_returns_immutable_tuple(self, batch: Batch) -> None:
        """Invariant: records property returns immutable copy."""
        batch.add_record({"id": "1"})

        records = batch.records
        assert isinstance(records, tuple)

        with pytest.raises((TypeError, AttributeError)):
            records.append(None)  # type: ignore

    def test_metadata_returns_copy(self, run_id: RunID) -> None:
        """Invariant: metadata returns a copy."""
        batch = Batch.create(
            run_id=run_id, created_at=_ts(0), metadata={"key": "value"}
        )

        metadata = batch.metadata
        metadata["new_key"] = "new_value"

        assert "new_key" not in batch.metadata


# ──────────────────────────────────────────────────────────────────────────────
# Domain Events Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestBatchDomainEvents:
    """Tests for domain event generation."""

    def test_create_emits_batch_created_event(self, run_id: RunID) -> None:
        """create() should emit BatchCreated event."""
        batch = Batch.create(run_id=run_id, created_at=_ts(0))

        events = batch.collect_events()
        assert len(events) == 1
        assert events[0].__class__.__name__ == "BatchCreated"
        assert events[0].occurred_at == _ts(0)

    def test_batch_domain_events_seal_emits_batch_sealed_event(
        self, batch: Batch
    ) -> None:
        """seal() should emit BatchSealed event."""
        batch.collect_events()  # Clear creation event
        batch.add_record({"id": "1"})
        batch.seal(_ts(10))

        events = batch.collect_events()
        assert len(events) == 1
        assert events[0].__class__.__name__ == "BatchSealed"
        assert events[0].occurred_at == _ts(10)

    def test_quarantine_emits_record_quarantined_event(self, batch: Batch) -> None:
        """quarantine_record() should emit RecordQuarantined event."""
        batch.collect_events()  # Clear creation event
        record = batch.add_record({"id": "1"})
        batch.quarantine_record(record, "Error", "ERR", quarantined_at=_ts(10))

        events = batch.collect_events()
        assert len(events) == 1
        assert events[0].__class__.__name__ == "RecordQuarantined"
        assert events[0].occurred_at == _ts(10)

    def test_committed_emits_batch_written_event(self, batch: Batch) -> None:
        """mark_committed() should emit BatchWritten event."""
        batch.collect_events()  # Clear creation event
        batch.add_record({"id": "1"})
        batch.seal(_ts(10))
        batch.mark_writing()
        batch.collect_events()  # Clear sealed event
        batch.mark_committed("silver", _ts(20))

        events = batch.collect_events()
        assert len(events) == 1
        assert events[0].__class__.__name__ == "BatchWritten"
        assert events[0].layer == "silver"
        assert events[0].occurred_at == _ts(20)


# ──────────────────────────────────────────────────────────────────────────────
# BatchStatus Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestBatchStatus:
    """Tests for BatchStatus enum behavior."""

    def test_only_open_is_modifiable(self) -> None:
        """Only OPEN status should allow modifications."""
        assert BatchStatus.OPEN.is_modifiable()
        assert not BatchStatus.SEALED.is_modifiable()
        assert not BatchStatus.WRITING.is_modifiable()
        assert not BatchStatus.COMMITTED.is_modifiable()
        assert not BatchStatus.FAILED.is_modifiable()


# ──────────────────────────────────────────────────────────────────────────────
# Constructor Validation Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestBatchConstructorValidation:
    """Tests for constructor validation."""

    def test_start_index_cannot_be_negative(self, run_id: RunID) -> None:
        """Invariant: start_index >= 0."""
        with pytest.raises(ValueError, match="cannot be negative"):
            Batch(
                batch_id=BatchID(
                    deterministic_uuid_value("unit.batch.constructor_validation")
                ),
                run_id=run_id,
                start_index=-1,
                created_at=_ts(0),
            )
