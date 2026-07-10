"""Tests for Batch aggregate internal modules.

This test file provides focused coverage for Batch internal modules:
- _batch_lifecycle.py: State transition functions and event emission
- _batch_mixins.py: Internal mixins for mutations and read model
- _batch_record.py: Value object invariants and transformations
- _batch_aggregate.py: Aggregate root construction and deterministic ID generation

These tests complement the existing test_batch.py by testing internal
functions directly rather than only through the public Batch API.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

import bioetl.domain.aggregates._batch_lifecycle as lifecycle
from bioetl.domain.aggregates._batch_record import BatchRecord
from bioetl.domain.aggregates._batch_status import BatchStatus
from bioetl.domain.aggregates.batch import Batch
from bioetl.domain.aggregates.events import (
    BatchCreated,
    BatchFailed,
    BatchSealed,
    BatchWritten,
    RecordQuarantined,
)
from bioetl.domain.exceptions import InvalidStateError
from bioetl.domain.medallion import Layer
from bioetl.domain.types import BatchID, ContentHash, EntityID, RunID
from tests.helpers.deterministic_ids import (
    deterministic_batch_uuid,
    deterministic_run_uuid,
)

pytestmark = pytest.mark.unit


def _ts(offset_seconds: int = 0) -> datetime:
    """Return deterministic UTC timestamps for batch tests."""
    return datetime(2026, 1, 1, tzinfo=UTC) + timedelta(seconds=offset_seconds)


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def run_id() -> RunID:
    """Create a test run ID."""
    return deterministic_run_uuid("batch_internal")


@pytest.fixture
def batch_id() -> BatchID:
    """Create a test batch ID."""
    return deterministic_batch_uuid("batch_internal")


@pytest.fixture
def sample_record_data():
    """Sample Bronze record data for testing."""
    return {"id": "mol-1", "smiles": "CCO", "activity": 0.5}


@pytest.fixture
def sample_batch_record(sample_record_data):
    """Create a sample BatchRecord for testing."""
    return BatchRecord(
        index=0,
        entity_id=EntityID("mol-1"),
        content_hash=ContentHash("abc123"),
        data=sample_record_data,
        is_valid=True,
    )


# ──────────────────────────────────────────────────────────────────────────────
# _batch_lifecycle.py Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestBatchLifecycleFunctions:
    """Tests for lifecycle functions in _batch_lifecycle.py."""

    def test_emit_batch_created_appends_event(self, run_id, batch_id):
        """emit_batch_created should append BatchCreated event."""
        events: list = []
        lifecycle.emit_batch_created(events, _ts(0), run_id, batch_id)

        assert len(events) == 1
        event = events[0]
        assert isinstance(event, BatchCreated)
        assert event.occurred_at == _ts(0)
        assert event.run_id == run_id
        assert event.batch_id == batch_id
        assert event.record_count == 0

    def test_seal_validates_open_status(self, run_id, batch_id):
        """seal should only transition from OPEN status."""
        events: list = []

        # Should succeed from OPEN
        new_status, sealed_at = lifecycle.seal(
            BatchStatus.OPEN, events, run_id, batch_id, 10, 8, 2, _ts(10)
        )
        assert new_status == BatchStatus.SEALED
        assert sealed_at == _ts(10)

        # Should fail from SEALED
        events.clear()
        with pytest.raises(InvalidStateError, match="Cannot seal"):
            lifecycle.seal(
                BatchStatus.SEALED, events, run_id, batch_id, 10, 8, 2, _ts(11)
            )

        # Should fail from WRITING
        with pytest.raises(InvalidStateError, match="Cannot seal"):
            lifecycle.seal(
                BatchStatus.WRITING, events, run_id, batch_id, 10, 8, 2, _ts(11)
            )

        # Should fail from COMMITTED
        with pytest.raises(InvalidStateError, match="Cannot seal"):
            lifecycle.seal(
                BatchStatus.COMMITTED, events, run_id, batch_id, 10, 8, 2, _ts(11)
            )

        # Should fail from FAILED
        with pytest.raises(InvalidStateError, match="Cannot seal"):
            lifecycle.seal(
                BatchStatus.FAILED, events, run_id, batch_id, 10, 8, 2, _ts(12)
            )

    def test_batch_lifecycle_seal_emits_batch_sealed_event(self, run_id, batch_id):
        """seal should emit BatchSealed event with correct counts."""
        events: list = []
        lifecycle.seal(BatchStatus.OPEN, events, run_id, batch_id, 10, 8, 2, _ts(10))

        assert len(events) == 1
        event = events[0]
        assert isinstance(event, BatchSealed)
        assert event.record_count == 10
        assert event.valid_count == 8
        assert event.quarantined_count == 2
        assert event.occurred_at == _ts(10)

    def test_mark_writing_validates_sealed_status(self):
        """mark_writing should only transition from SEALED."""
        # Should succeed from SEALED
        assert lifecycle.mark_writing(BatchStatus.SEALED) == BatchStatus.WRITING

        # Should fail from OPEN
        with pytest.raises(InvalidStateError, match="Cannot mark as writing"):
            lifecycle.mark_writing(BatchStatus.OPEN)

        # Should fail from WRITING
        with pytest.raises(InvalidStateError, match="Cannot mark as writing"):
            lifecycle.mark_writing(BatchStatus.WRITING)

        # Should fail from COMMITTED
        with pytest.raises(InvalidStateError, match="Cannot mark as writing"):
            lifecycle.mark_writing(BatchStatus.COMMITTED)

        # Should fail from FAILED
        with pytest.raises(InvalidStateError, match="Cannot mark as writing"):
            lifecycle.mark_writing(BatchStatus.FAILED)

    def test_mark_committed_validates_writing_status(self, run_id, batch_id):
        """mark_committed should only transition from WRITING."""
        events: list = []

        # Should succeed from WRITING
        new_status = lifecycle.mark_committed(
            BatchStatus.WRITING, events, run_id, batch_id, 8, Layer.SILVER, _ts(20)
        )
        assert new_status == BatchStatus.COMMITTED

        # Should fail from OPEN
        with pytest.raises(InvalidStateError, match="Cannot commit"):
            lifecycle.mark_committed(
                BatchStatus.OPEN, events, run_id, batch_id, 8, Layer.SILVER, _ts(20)
            )

        # Should fail from SEALED
        with pytest.raises(InvalidStateError, match="Cannot commit"):
            lifecycle.mark_committed(
                BatchStatus.SEALED, events, run_id, batch_id, 8, Layer.SILVER, _ts(20)
            )

        # Should fail from COMMITTED
        with pytest.raises(InvalidStateError, match="Cannot commit"):
            lifecycle.mark_committed(
                BatchStatus.COMMITTED, events, run_id, batch_id, 8, Layer.SILVER, _ts(20)
            )

        # Should fail from FAILED
        with pytest.raises(InvalidStateError, match="Cannot commit"):
            lifecycle.mark_committed(
                BatchStatus.FAILED, events, run_id, batch_id, 8, Layer.SILVER, _ts(20)
            )

    def test_lifecycle_mark_committed_emits_batch_written_event(self, run_id, batch_id):
        """mark_committed should emit BatchWritten event."""
        events: list = []
        lifecycle.mark_committed(
            BatchStatus.WRITING, events, run_id, batch_id, 8, Layer.SILVER, _ts(20)
        )

        assert len(events) == 1
        event = events[0]
        assert isinstance(event, BatchWritten)
        assert event.run_id == run_id
        assert event.batch_id == batch_id
        assert event.layer is Layer.SILVER
        assert event.record_count == 8
        assert event.occurred_at == _ts(20)

    def test_mark_failed_validates_writing_status(self, run_id, batch_id):
        """mark_failed should only transition from WRITING."""
        events: list = []

        # Should succeed from WRITING
        new_status = lifecycle.mark_failed(
            BatchStatus.WRITING,
            events,
            run_id,
            batch_id,
            Layer.SILVER,
            "Write error",
            None,
            failed_at=_ts(20),
        )
        assert new_status == BatchStatus.FAILED

        # Should fail from OPEN
        with pytest.raises(InvalidStateError, match="Cannot fail"):
            lifecycle.mark_failed(
                BatchStatus.OPEN,
                events,
                run_id,
                batch_id,
                Layer.SILVER,
                "Error",
                None,
                failed_at=_ts(20),
            )

        # Should fail from SEALED
        with pytest.raises(InvalidStateError, match="Cannot fail"):
            lifecycle.mark_failed(
                BatchStatus.SEALED,
                events,
                run_id,
                batch_id,
                Layer.SILVER,
                "Error",
                None,
                failed_at=_ts(20),
            )

        # Should fail from COMMITTED
        with pytest.raises(InvalidStateError, match="Cannot fail"):
            lifecycle.mark_failed(
                BatchStatus.COMMITTED,
                events,
                run_id,
                batch_id,
                Layer.SILVER,
                "Error",
                None,
                failed_at=_ts(20),
            )

        # Should fail from FAILED
        with pytest.raises(InvalidStateError, match="Cannot fail"):
            lifecycle.mark_failed(
                BatchStatus.FAILED,
                events,
                run_id,
                batch_id,
                Layer.SILVER,
                "Error",
                None,
                failed_at=_ts(20),
            )

    def test_lifecycle_mark_failed_emits_batch_failed_event(self, run_id, batch_id):
        """mark_failed should emit BatchFailed event with error details."""
        events: list = []
        lifecycle.mark_failed(
            BatchStatus.WRITING,
            events,
            run_id,
            batch_id,
            Layer.SILVER,
            "Connection timeout",
            "TimeoutError",
            failed_at=_ts(20),
        )

        assert len(events) == 1
        event = events[0]
        assert isinstance(event, BatchFailed)
        assert event.run_id == run_id
        assert event.batch_id == batch_id
        assert event.layer is Layer.SILVER
        assert event.error == "Connection timeout"
        assert event.error_type == "TimeoutError"
        assert event.occurred_at == _ts(20)

    def test_emit_record_quarantined_appends_event(self, run_id, batch_id):
        """emit_record_quarantined should append RecordQuarantined event."""
        events: list = []
        lifecycle.emit_record_quarantined(
            events,
            run_id,
            batch_id,
            EntityID("mol-1"),
            "SCHEMA_VIOLATION",
            "Missing required field",
            ContentHash("abc123"),
            _ts(5),
        )

        assert len(events) == 1
        event = events[0]
        assert isinstance(event, RecordQuarantined)
        assert event.record_id == "mol-1"
        assert event.error_code == "SCHEMA_VIOLATION"
        assert event.error_message == "Missing required field"
        assert event.content_hash == ContentHash("abc123")
        assert event.batch_id == batch_id
        assert event.run_id == run_id
        assert event.occurred_at == _ts(5)

    def test_emit_record_quarantined_handles_null_entity_id(self, run_id, batch_id):
        """emit_record_quarantined should handle None entity_id."""
        events: list = []
        lifecycle.emit_record_quarantined(
            events,
            run_id,
            batch_id,
            None,
            None,
            "Parse error",
            None,
            _ts(5),
        )

        assert len(events) == 1
        event = events[0]
        assert event.record_id is None
        assert event.error_code is None
        assert event.content_hash is None


# ──────────────────────────────────────────────────────────────────────────────
# _batch_mixins.py Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestBatchReadModelMixin:
    """Tests for _BatchReadModelMixin properties and methods."""

    def test_batch_read_model_property_accessors_return_correct_values(self, run_id):
        """Read model properties should return correct aggregate state."""
        batch = Batch.create(
            run_id=run_id, start_index=100, created_at=_ts(0), metadata={"key": "value"}
        )
        batch.add_record({"id": "1"})
        batch.add_record({"id": "2"})

        assert batch.batch_id is not None
        assert batch.run_id == run_id
        assert batch.status == BatchStatus.OPEN
        assert batch.record_count == 2
        assert batch.valid_count == 2
        assert batch.quarantined_count == 0
        assert batch.next_index == 102
        assert batch.created_at == _ts(0)
        assert batch.sealed_at is None
        assert batch.metadata == {"key": "value"}

    def test_records_property_filters_valid_records(self, run_id):
        """records property should only return valid records."""
        batch = Batch.create(run_id=run_id, created_at=_ts(0))
        record1 = batch.add_record({"id": "1"})
        record2 = batch.add_record({"id": "2"})
        batch.quarantine_record(record1, "Error", "ERR", quarantined_at=_ts(5))

        assert len(batch.records) == 1
        assert batch.records[0] == record2
        assert len(batch.all_records) == 2
        assert len(batch.quarantined_records) == 1

    def test_quarantined_records_property(self, run_id):
        """quarantined_records should return only quarantined records."""
        batch = Batch.create(run_id=run_id, created_at=_ts(0))
        record1 = batch.add_record({"id": "1"}, entity_id=EntityID("mol-1"))
        batch.add_record({"id": "2"}, entity_id=EntityID("mol-2"))
        record3 = batch.add_record({"id": "3"}, entity_id=EntityID("mol-3"))
        batch.quarantine_record(record1, "Error1", "ERR1", quarantined_at=_ts(5))
        batch.quarantine_record(record3, "Error2", "ERR2", quarantined_at=_ts(6))

        assert len(batch.quarantined_records) == 2
        quarantined_ids = {r.entity_id for r in batch.quarantined_records}
        assert len(quarantined_ids) == 2

    def test_batch_read_model_collect_events_clears_event_list(self, run_id):
        """collect_events should return and clear accumulated events."""
        batch = Batch.create(run_id=run_id, created_at=_ts(0))
        batch.add_record({"id": "1"})
        batch.seal(_ts(10))

        events = batch.collect_events()
        assert len(events) == 2  # BatchCreated + BatchSealed

        # Second call should return empty list
        events2 = batch.collect_events()
        assert len(events2) == 0

    def test_batch_read_model_repr_includes_key_state(self, run_id):
        """__repr__ should include key aggregate state."""
        batch = Batch.create(run_id=run_id, created_at=_ts(0))
        batch.add_record({"id": "1"})
        batch.add_record({"id": "2"})
        batch.quarantine_record(
            batch.all_records[0], "Error", "ERR", quarantined_at=_ts(5)
        )

        repr_str = repr(batch)
        assert "Batch(" in repr_str
        assert "status=" in repr_str
        assert "records=2" in repr_str
        assert "valid=1" in repr_str
        assert "quarantined=1" in repr_str


class TestBatchMutationMixin:
    """Tests for _BatchMutationMixin record operations."""

    def test_add_record_creates_record_with_next_index(self, run_id):
        """add_record should create record with sequential index."""
        batch = Batch.create(run_id=run_id, start_index=50, created_at=_ts(0))

        record1 = batch.add_record({"id": "1"})
        assert record1.index == 50

        record2 = batch.add_record({"id": "2"})
        assert record2.index == 51

    def test_add_record_with_entity_id_and_hash(self, run_id):
        """add_record should store entity_id and content_hash."""
        batch = Batch.create(run_id=run_id, created_at=_ts(0))

        record = batch.add_record(
            {"id": "1"},
            entity_id=EntityID("mol-1"),
            content_hash=ContentHash("abc123"),
        )

        assert record.entity_id == EntityID("mol-1")
        assert record.content_hash == ContentHash("abc123")
        assert record.is_valid

    def test_add_records_creates_multiple_records(self, run_id):
        """add_records should create multiple records at once."""
        batch = Batch.create(run_id=run_id, created_at=_ts(0))

        records = batch.add_records(
            [
                {"id": "1"},
                {"id": "2"},
                {"id": "3"},
            ]
        )

        assert len(records) == 3
        assert batch.record_count == 3
        assert [r.index for r in records] == [0, 1, 2]

    def test_quarantine_record_updates_record_in_place(self, run_id):
        """quarantine_record should replace record in _records list."""
        batch = Batch.create(run_id=run_id, created_at=_ts(0))
        record = batch.add_record({"id": "1"})

        assert record.is_valid
        assert batch.valid_count == 1

        quarantined = batch.quarantine_record(
            record, "Schema error", "SCHEMA", quarantined_at=_ts(5)
        )

        assert not quarantined.is_valid
        assert quarantined.error == "Schema error"
        assert batch.valid_count == 0
        assert batch.quarantined_count == 1

    def test_quarantine_record_adds_to_quarantined_list(self, run_id):
        """quarantine_record should append to _quarantined list."""
        batch = Batch.create(run_id=run_id, created_at=_ts(0))
        record = batch.add_record({"id": "1"})

        batch.quarantine_record(record, "Error", "ERR", quarantined_at=_ts(5))

        assert len(batch.quarantined_records) == 1
        # The quarantined record should have the same index as the original
        assert batch.quarantined_records[0].index == record.index
        # But should be marked as invalid
        assert not batch.quarantined_records[0].is_valid

    def test_quarantine_record_emits_event(self, run_id):
        """quarantine_record should emit RecordQuarantined event."""
        batch = Batch.create(run_id=run_id, created_at=_ts(0))
        batch.collect_events()  # Clear creation event
        record = batch.add_record({"id": "1"})

        batch.quarantine_record(record, "Error", "ERR", quarantined_at=_ts(5))

        events = batch.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], RecordQuarantined)

    def test_quarantine_record_raises_for_foreign_record(self, run_id):
        """quarantine_record should raise ValueError for record from another batch."""
        batch1 = Batch.create(run_id=run_id, created_at=_ts(0))
        batch2 = Batch.create(run_id=run_id, created_at=_ts(1))

        foreign_record = batch1.add_record({"id": "1"})
        batch2.add_record({"id": "2"})

        with pytest.raises(ValueError, match="does not belong to this batch"):
            batch2.quarantine_record(
                foreign_record, "Error", "ERR", quarantined_at=_ts(5)
            )

    def test_assert_open_blocks_operations_on_sealed(self, run_id):
        """_assert_open should raise InvalidStateError for non-modifiable states."""
        batch = Batch.create(run_id=run_id, created_at=_ts(0))
        batch.add_record({"id": "1"})
        batch.seal(_ts(10))

        with pytest.raises(InvalidStateError, match="Cannot add_record"):
            batch.add_record({"id": "2"})

        with pytest.raises(InvalidStateError, match="Cannot quarantine_record"):
            batch.quarantine_record(
                batch.all_records[0], "Error", "ERR", quarantined_at=_ts(11)
            )


class TestBatchLifecycleMixin:
    """Tests for _BatchLifecycleMixin state transition methods."""

    def test_seal_delegates_to_lifecycle_function(self, run_id):
        """seal should delegate to lifecycle.seal with correct parameters."""
        batch = Batch.create(run_id=run_id, created_at=_ts(0))
        batch.add_record({"id": "1"})
        batch.collect_events()  # Clear creation event

        batch.seal(_ts(10))

        assert batch.status == BatchStatus.SEALED
        assert batch.sealed_at == _ts(10)

        events = batch.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], BatchSealed)

    def test_mark_writing_delegates_to_lifecycle_function(self, run_id):
        """mark_writing should delegate to lifecycle.mark_writing."""
        batch = Batch.create(run_id=run_id, created_at=_ts(0))
        batch.add_record({"id": "1"})
        batch.seal(_ts(10))

        batch.mark_writing()

        assert batch.status == BatchStatus.WRITING

    def test_mark_committed_delegates_to_lifecycle_function(self, run_id):
        """mark_committed should delegate to lifecycle.mark_committed."""
        batch = Batch.create(run_id=run_id, created_at=_ts(0))
        batch.add_record({"id": "1"})
        batch.seal(_ts(10))
        batch.mark_writing()
        batch.collect_events()  # Clear previous events

        batch.mark_committed(Layer.SILVER, _ts(20))

        assert batch.status == BatchStatus.COMMITTED

        events = batch.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], BatchWritten)
        assert events[0].layer is Layer.SILVER

    def test_mark_failed_delegates_to_lifecycle_function(self, run_id):
        """mark_failed should delegate to lifecycle.mark_failed."""
        batch = Batch.create(run_id=run_id, created_at=_ts(0))
        batch.add_record({"id": "1"})
        batch.seal(_ts(10))
        batch.mark_writing()
        batch.collect_events()  # Clear previous events

        batch.mark_failed(Layer.BRONZE, "Write error", "IOError", failed_at=_ts(20))

        assert batch.status == BatchStatus.FAILED

        events = batch.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], BatchFailed)
        assert events[0].run_id == run_id
        assert events[0].batch_id == batch.batch_id
        assert events[0].layer is Layer.BRONZE
        assert events[0].error == "Write error"
        assert events[0].error_type == "IOError"

    def test_mark_writing_invalid_without_seal(self, run_id):
        """mark_writing should require SEALED status."""
        batch = Batch.create(run_id=run_id, created_at=_ts(0))
        batch.add_record({"id": "1"})

        with pytest.raises(InvalidStateError, match="Cannot mark as writing"):
            batch.mark_writing()

    def test_mark_committed_invalid_without_writing(self, run_id):
        """mark_committed should require WRITING status on aggregate level."""
        batch = Batch.create(run_id=run_id, created_at=_ts(0))
        batch.add_record({"id": "1"})
        batch.seal(_ts(10))

        with pytest.raises(InvalidStateError, match="Cannot commit"):
            batch.mark_committed(Layer.SILVER, _ts(20))

    def test_mark_failed_invalid_without_writing(self, run_id):
        """mark_failed should require WRITING status on aggregate level."""
        batch = Batch.create(run_id=run_id, created_at=_ts(0))
        batch.add_record({"id": "1"})
        batch.seal(_ts(10))

        with pytest.raises(InvalidStateError, match="Cannot fail"):
            batch.mark_failed(Layer.BRONZE, "Write error", "IOError", failed_at=_ts(20))

    def test_quarantine_record_event_payloads(self, run_id):
        """quarantine_record should emit full RecordQuarantined payload."""
        batch = Batch.create(run_id=run_id, created_at=_ts(0))
        batch.collect_events()  # Clear creation event
        record = batch.add_record({"id": "1"})

        batch.quarantine_record(
            record,
            "Schema validation error",
            "SCHEMA",
            quarantined_at=_ts(5),
        )

        event = batch.collect_events()[0]
        assert isinstance(event, RecordQuarantined)
        assert event.run_id == run_id
        assert event.batch_id == batch.batch_id
        assert event.record_id is None
        assert event.error_code == "SCHEMA"
        assert event.error_message == "Schema validation error"
        assert event.content_hash is None


# ──────────────────────────────────────────────────────────────────────────────
# _batch_record.py Additional Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestBatchRecordValueObject:
    """Additional tests for BatchRecord value object."""

    def test_batch_record_with_all_fields(self):
        """BatchRecord should handle all optional fields."""
        record = BatchRecord(
            index=10,
            entity_id=EntityID("mol-1"),
            content_hash=ContentHash("abc123"),
            data={"id": "1", "smiles": "CCO"},
            is_valid=False,
            error="Validation failed",
            error_code="SCHEMA_VIOLATION",
        )

        assert record.index == 10
        assert record.entity_id == EntityID("mol-1")
        assert record.content_hash == ContentHash("abc123")
        assert not record.is_valid
        assert record.error == "Validation failed"
        assert record.error_code == "SCHEMA_VIOLATION"

    def test_batch_record_defaults_to_valid(self):
        """BatchRecord should default to valid when is_valid not specified."""
        record = BatchRecord(
            index=0,
            entity_id=None,
            content_hash=None,
            data={"id": "1"},
        )

        assert record.is_valid
        assert record.error is None
        assert record.error_code is None

    def test_with_validation_error_preserves_data(self, sample_batch_record):
        """with_validation_error should preserve all data fields."""
        invalid = sample_batch_record.with_validation_error("Test error", "TEST")

        assert invalid.data == sample_batch_record.data
        assert invalid.index == sample_batch_record.index
        assert invalid.entity_id == sample_batch_record.entity_id
        assert invalid.content_hash == sample_batch_record.content_hash

    def test_with_validation_error_overrides_validation_fields(
        self, sample_batch_record
    ):
        """with_validation_error should override validation-related fields."""
        invalid = sample_batch_record.with_validation_error("New error", "NEW_CODE")

        assert not invalid.is_valid
        assert invalid.error == "New error"
        assert invalid.error_code == "NEW_CODE"

    def test_batch_record_post_init_validates_index(self):
        """__post_init__ should validate index >= 0."""
        with pytest.raises(ValueError, match="cannot be negative"):
            BatchRecord(
                index=-1,
                entity_id=None,
                content_hash=None,
                data={"id": "1"},
            )

    def test_batch_record_post_init_validates_invalid_record_has_error(self):
        """__post_init__ should validate that invalid records have error message."""
        with pytest.raises(ValueError, match="must have an error"):
            BatchRecord(
                index=0,
                entity_id=None,
                content_hash=None,
                data={"id": "1"},
                is_valid=False,
                error=None,
            )


# ──────────────────────────────────────────────────────────────────────────────
# _batch_aggregate.py Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestBatchAggregateRoot:
    """Tests for Batch aggregate root construction and deterministic ID generation."""

    def test_batch_constructor_validates_start_index(self, run_id, batch_id):
        """Batch constructor should validate start_index >= 0."""
        with pytest.raises(ValueError, match="cannot be negative"):
            Batch(
                batch_id=batch_id,
                run_id=run_id,
                start_index=-1,
                created_at=_ts(0),
            )

    def test_batch_create_generates_deterministic_id(self, run_id):
        """Batch.create should generate deterministic BatchID from parameters."""
        batch1 = Batch.create(
            run_id=run_id,
            start_index=0,
            created_at=_ts(0),
            metadata={"key": "value"},
        )
        batch2 = Batch.create(
            run_id=run_id,
            start_index=0,
            created_at=_ts(0),
            metadata={"key": "value"},
        )

        # Same parameters should produce same ID
        assert batch1.batch_id == batch2.batch_id

    def test_batch_create_different_parameters_different_ids(self, run_id):
        """Batch.create should generate different IDs for different parameters."""
        batch1 = Batch.create(
            run_id=run_id,
            start_index=0,
            created_at=_ts(0),
        )
        batch2 = Batch.create(
            run_id=run_id,
            start_index=1,  # Different start_index
            created_at=_ts(0),
        )

        assert batch1.batch_id != batch2.batch_id

    def test_batch_create_with_metadata(self, run_id):
        """Batch.create should accept and store metadata."""
        metadata = {"source": "test", "version": "1.0"}
        batch = Batch.create(
            run_id=run_id,
            created_at=_ts(0),
            metadata=metadata,
        )

        assert batch.metadata == metadata

    def test_batch_create_emits_batch_created_event(self, run_id):
        """Batch.create should emit BatchCreated event."""
        batch = Batch.create(run_id=run_id, created_at=_ts(0))

        events = batch.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], BatchCreated)
        assert events[0].occurred_at == _ts(0)
        assert events[0].run_id == run_id

    def test_batch_initial_state_is_open(self, run_id):
        """Batch should start in OPEN status with empty records."""
        batch = Batch.create(run_id=run_id, created_at=_ts(0))

        assert batch.status == BatchStatus.OPEN
        assert batch.record_count == 0
        assert batch.valid_count == 0
        assert batch.quarantined_count == 0
        assert batch.sealed_at is None
