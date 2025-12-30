"""Batch Aggregate.

Aggregate Root for a collection of records being processed together.

Invariants:
    1. All records in a batch have the same batch_id
    2. Records cannot be added after the batch is sealed
    3. batch_id is unique and immutable
    4. Record indices are sequential starting from start_index
    5. Quarantined records are tracked separately from valid records

Consistency Boundary:
    - Record additions and status changes are transactionally consistent
    - Sealing the batch is an atomic operation
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from bioetl.domain.exceptions import InvalidStateError
from bioetl.domain.types import BatchID, ContentHash, EntityID, RunID


class BatchStatus(str, Enum):
    """Status of a batch."""

    OPEN = "open"
    """Batch is accepting new records."""

    SEALED = "sealed"
    """Batch is sealed, no more records can be added."""

    WRITING = "writing"
    """Batch is being written to storage."""

    COMMITTED = "committed"
    """Batch has been successfully written."""

    FAILED = "failed"
    """Batch write failed."""

    def is_modifiable(self) -> bool:
        """Check if records can still be added."""
        return self == BatchStatus.OPEN


@dataclass(frozen=True, slots=True)
class BatchRecord:
    """Immutable value object representing a record in a batch.

    Attributes:
        index: Sequential index within the batch.
        entity_id: Business key for the entity.
        content_hash: SHA256 hash for versioning.
        data: The actual record data.
        is_valid: Whether the record passed validation.
        error: Error message if validation failed.
        error_code: Error classification code.
    """

    index: int
    entity_id: EntityID | None
    content_hash: ContentHash | None
    data: dict[str, Any]
    is_valid: bool = True
    error: str | None = None
    error_code: str | None = None

    def __post_init__(self) -> None:
        """Validate record invariants."""
        if self.index < 0:
            raise ValueError(f"Record index cannot be negative: {self.index}")
        if not self.is_valid and not self.error:
            raise ValueError("Invalid record must have an error message")

    def with_validation_error(
        self, error: str, error_code: str | None = None
    ) -> BatchRecord:
        """Create a new BatchRecord marked as invalid.

        Args:
            error: Error message.
            error_code: Error classification.

        Returns:
            New BatchRecord with is_valid=False.
        """
        return BatchRecord(
            index=self.index,
            entity_id=self.entity_id,
            content_hash=self.content_hash,
            data=self.data,
            is_valid=False,
            error=error,
            error_code=error_code,
        )


class Batch:
    """Aggregate Root for a collection of records.

    Invariants:
        1. All records have the same batch_id (enforced by aggregate)
        2. Records cannot be added after sealing
        3. batch_id is immutable
        4. Record indices are sequential

    Example:
        >>> batch = Batch.create(run_id=run_id)
        >>> batch.add_record({"id": "1", "value": 100})
        >>> batch.add_record({"id": "2", "value": 200})
        >>> batch.seal()
        >>> events = batch.collect_events()
    """

    __slots__ = (
        "_batch_id",
        "_created_at",
        "_events",
        "_metadata",
        "_quarantined",
        "_records",
        "_run_id",
        "_sealed_at",
        "_start_index",
        "_status",
    )

    def __init__(
        self,
        batch_id: BatchID,
        run_id: RunID,
        start_index: int = 0,
        created_at: datetime | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Initialize a new batch.

        Args:
            batch_id: Unique identifier for this batch.
            run_id: Parent run identifier for lineage.
            start_index: Starting index for records (for continuation).
            created_at: Creation timestamp.
            metadata: Optional additional metadata.
        """
        if start_index < 0:
            raise ValueError(f"start_index cannot be negative: {start_index}")

        self._batch_id = batch_id
        self._run_id = run_id
        self._status = BatchStatus.OPEN
        self._records: list[BatchRecord] = []
        self._quarantined: list[BatchRecord] = []
        self._start_index = start_index
        self._created_at = created_at or datetime.now(UTC)
        self._sealed_at: datetime | None = None
        self._events: list[Any] = []
        self._metadata = metadata or {}

    @classmethod
    def create(
        cls,
        run_id: RunID,
        start_index: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> Batch:
        """Factory method to create a new batch with generated ID.

        Args:
            run_id: Parent run identifier.
            start_index: Starting index for records.
            metadata: Optional metadata.

        Returns:
            New Batch instance with generated batch_id.
        """
        from uuid import uuid4

        batch_id = BatchID(uuid4())
        batch = cls(
            batch_id=batch_id,
            run_id=run_id,
            start_index=start_index,
            metadata=metadata,
        )

        # Emit creation event
        from bioetl.domain.aggregates.events import BatchCreated

        batch._events.append(
            BatchCreated(
                occurred_at=batch._created_at,
                run_id=run_id,
                batch_id=batch_id,
                record_count=0,
            )
        )
        return batch

    # ──────────────────────────────────────────────────────────────────────────
    # Read-only properties
    # ──────────────────────────────────────────────────────────────────────────

    @property
    def batch_id(self) -> BatchID:
        """Immutable batch identifier."""
        return self._batch_id

    @property
    def run_id(self) -> RunID:
        """Parent run identifier."""
        return self._run_id

    @property
    def status(self) -> BatchStatus:
        """Current batch status."""
        return self._status

    @property
    def records(self) -> tuple[BatchRecord, ...]:
        """Immutable tuple of valid records."""
        return tuple(r for r in self._records if r.is_valid)

    @property
    def all_records(self) -> tuple[BatchRecord, ...]:
        """All records including invalid ones."""
        return tuple(self._records)

    @property
    def quarantined_records(self) -> tuple[BatchRecord, ...]:
        """Records that failed validation."""
        return tuple(self._quarantined)

    @property
    def record_count(self) -> int:
        """Total number of records added."""
        return len(self._records)

    @property
    def valid_count(self) -> int:
        """Number of valid records."""
        return sum(1 for r in self._records if r.is_valid)

    @property
    def quarantined_count(self) -> int:
        """Number of quarantined records."""
        return len(self._quarantined)

    @property
    def next_index(self) -> int:
        """Next available record index."""
        return self._start_index + len(self._records)

    @property
    def created_at(self) -> datetime:
        """Batch creation timestamp."""
        return self._created_at

    @property
    def sealed_at(self) -> datetime | None:
        """Timestamp when batch was sealed."""
        return self._sealed_at

    @property
    def metadata(self) -> dict[str, Any]:
        """Copy of batch metadata."""
        return self._metadata.copy()

    # ──────────────────────────────────────────────────────────────────────────
    # Record management methods
    # ──────────────────────────────────────────────────────────────────────────

    def add_record(
        self,
        data: dict[str, Any],
        entity_id: EntityID | None = None,
        content_hash: ContentHash | None = None,
    ) -> BatchRecord:
        """Add a record to the batch.

        Args:
            data: The record data.
            entity_id: Optional business key.
            content_hash: Optional content hash for versioning.

        Returns:
            The created BatchRecord.

        Raises:
            InvalidStateError: If batch is not OPEN.
        """
        self._assert_open("add_record")

        record = BatchRecord(
            index=self.next_index,
            entity_id=entity_id,
            content_hash=content_hash,
            data=data,
            is_valid=True,
        )
        self._records.append(record)
        return record

    def add_records(
        self,
        records: list[dict[str, Any]],
    ) -> list[BatchRecord]:
        """Add multiple records to the batch.

        Args:
            records: List of record data dictionaries.

        Returns:
            List of created BatchRecords.

        Raises:
            InvalidStateError: If batch is not OPEN.
        """
        self._assert_open("add_records")
        return [self.add_record(data) for data in records]

    def quarantine_record(
        self,
        record: BatchRecord,
        error: str,
        error_code: str | None = None,
    ) -> BatchRecord:
        """Mark a record as quarantined.

        Args:
            record: The record to quarantine.
            error: Error message.
            error_code: Error classification.

        Returns:
            The quarantined BatchRecord.

        Raises:
            InvalidStateError: If batch is not OPEN.
            ValueError: If record is not in this batch.
        """
        self._assert_open("quarantine_record")

        # Verify record belongs to this batch
        if record not in self._records:
            raise ValueError("Record does not belong to this batch")

        # Create invalid version
        quarantined = record.with_validation_error(error, error_code)

        # Update the record in place (replace with invalid version)
        idx = self._records.index(record)
        self._records[idx] = quarantined
        self._quarantined.append(quarantined)

        # Emit event
        from bioetl.domain.aggregates.events import RecordQuarantined

        self._events.append(
            RecordQuarantined(
                occurred_at=datetime.now(UTC),
                run_id=self._run_id,
                batch_id=self._batch_id,
                record_id=str(record.entity_id) if record.entity_id else None,
                error_code=error_code or "UNKNOWN",
                error_message=error,
                content_hash=record.content_hash,
            )
        )

        return quarantined

    # ──────────────────────────────────────────────────────────────────────────
    # Lifecycle methods
    # ──────────────────────────────────────────────────────────────────────────

    def seal(self, sealed_at: datetime | None = None) -> None:
        """Seal the batch, preventing further record additions.

        Transitions: OPEN -> SEALED

        Args:
            sealed_at: Seal timestamp.

        Raises:
            InvalidStateError: If batch is not OPEN.
        """
        self._assert_open("seal")
        self._status = BatchStatus.SEALED
        self._sealed_at = sealed_at or datetime.now(UTC)

        # Emit event
        from bioetl.domain.aggregates.events import BatchSealed

        self._events.append(
            BatchSealed(
                occurred_at=self._sealed_at,
                run_id=self._run_id,
                batch_id=self._batch_id,
                record_count=self.record_count,
                valid_count=self.valid_count,
                quarantined_count=self.quarantined_count,
            )
        )

    def mark_writing(self) -> None:
        """Mark batch as being written to storage.

        Transitions: SEALED -> WRITING

        Raises:
            InvalidStateError: If batch is not SEALED.
        """
        if self._status != BatchStatus.SEALED:
            raise InvalidStateError(
                f"Cannot mark as writing: batch is in status {self._status.value}",
                current_state=self._status.value,
                attempted_operation="mark_writing",
            )
        self._status = BatchStatus.WRITING

    def mark_committed(self, layer: str) -> None:
        """Mark batch as successfully committed to a layer.

        Transitions: WRITING -> COMMITTED

        Args:
            layer: The storage layer written to (bronze, silver, gold).

        Raises:
            InvalidStateError: If batch is not WRITING.
        """
        if self._status != BatchStatus.WRITING:
            raise InvalidStateError(
                f"Cannot commit: batch is in status {self._status.value}",
                current_state=self._status.value,
                attempted_operation="mark_committed",
            )
        self._status = BatchStatus.COMMITTED

        # Emit event
        from bioetl.domain.aggregates.events import BatchWritten

        self._events.append(
            BatchWritten(
                occurred_at=datetime.now(UTC),
                run_id=self._run_id,
                batch_id=self._batch_id,
                layer=layer,
                record_count=self.valid_count,
            )
        )

    def mark_failed(
        self, layer: str, error: str, error_type: str | None = None
    ) -> None:
        """Mark batch write as failed.

        Transitions: WRITING -> FAILED

        Args:
            layer: The storage layer that failed.
            error: Error message.
            error_type: Error classification.

        Raises:
            InvalidStateError: If batch is not WRITING.
        """
        if self._status != BatchStatus.WRITING:
            raise InvalidStateError(
                f"Cannot fail: batch is in status {self._status.value}",
                current_state=self._status.value,
                attempted_operation="mark_failed",
            )
        self._status = BatchStatus.FAILED

        # Emit event
        from bioetl.domain.aggregates.events import BatchFailed

        self._events.append(
            BatchFailed(
                occurred_at=datetime.now(UTC),
                run_id=self._run_id,
                batch_id=self._batch_id,
                layer=layer,
                error=error,
                error_type=error_type,
            )
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Domain events
    # ──────────────────────────────────────────────────────────────────────────

    def collect_events(self) -> list[Any]:
        """Collect and clear accumulated domain events.

        Returns:
            List of domain events.
        """
        events = self._events.copy()
        self._events.clear()
        return events

    # ──────────────────────────────────────────────────────────────────────────
    # Private helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _assert_open(self, operation: str) -> None:
        """Assert that the batch is OPEN for modifications.

        Raises:
            InvalidStateError: If not OPEN.
        """
        if not self._status.is_modifiable():
            raise InvalidStateError(
                f"Cannot {operation}: batch is in status {self._status.value}",
                current_state=self._status.value,
                attempted_operation=operation,
            )

    def __repr__(self) -> str:
        return (
            f"Batch(batch_id={self._batch_id!r}, "
            f"status={self._status.value!r}, "
            f"records={self.record_count}, "
            f"valid={self.valid_count}, "
            f"quarantined={self.quarantined_count})"
        )
