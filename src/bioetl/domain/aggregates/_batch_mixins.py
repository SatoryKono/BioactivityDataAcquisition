"""Internal mixins for Batch aggregate behavior."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from bioetl.domain.aggregates._batch_attrs import _BatchAttrs
import bioetl.domain.aggregates._batch_lifecycle as lifecycle
from bioetl.domain.aggregates._batch_record import BatchRecord
from bioetl.domain.aggregates._batch_status import BatchStatus
from bioetl.domain.exceptions import InvalidStateError

if TYPE_CHECKING:
    from bioetl.domain.types import (
        BronzeRecord,
        ContentHash,
        EntityID,
    )


class _BatchReadModelMixin(_BatchAttrs):
    """Read model projections and event collection."""

    __slots__ = ()

    @property
    def batch_id(self) -> BatchID:
        """Return the unique identifier for this batch."""
        return self._batch_id

    @property
    def run_id(self) -> RunID:
        """Return the pipeline run identifier that owns this batch."""
        return self._run_id

    @property
    def status(self) -> BatchStatus:
        """Return the current lifecycle status of this batch."""
        return self._status

    @property
    def records(self) -> tuple[BatchRecord, ...]:
        """Return valid (non-quarantined) records in insertion order."""
        return tuple(record for record in self._records if record.is_valid)

    @property
    def all_records(self) -> tuple[BatchRecord, ...]:
        """Return all records including quarantined ones in insertion order."""
        return tuple(self._records)

    @property
    def quarantined_records(self) -> tuple[BatchRecord, ...]:
        """Return records that failed validation and were quarantined."""
        return tuple(self._quarantined)

    @property
    def record_count(self) -> int:
        """Return the total number of records including quarantined."""
        return len(self._records)

    @property
    def valid_count(self) -> int:
        """Return the number of records that passed validation."""
        return sum(1 for record in self._records if record.is_valid)

    @property
    def quarantined_count(self) -> int:
        """Return the number of quarantined records."""
        return len(self._quarantined)

    @property
    def next_index(self) -> int:
        """Return the next sequential index for appending a record."""
        return self._start_index + len(self._records)

    @property
    def created_at(self) -> datetime:
        """Return the UTC timestamp when this batch was created."""
        return self._created_at

    @property
    def sealed_at(self) -> datetime | None:
        """Return the UTC timestamp when the batch was sealed, or None if still open."""
        return self._sealed_at

    @property
    def metadata(self) -> MetaDict:
        """Return a copy of the batch metadata dictionary."""
        return self._metadata.copy()

    def collect_events(self) -> list[DomainEvent]:
        """Collect and clear accumulated domain events."""
        events = self._events.copy()
        self._events.clear()
        return events

    def __repr__(self) -> str:
        return (
            f"Batch(batch_id={self._batch_id!r}, "
            f"status={self._status.value!r}, "
            f"records={self.record_count}, "
            f"valid={self.valid_count}, "
            f"quarantined={self.quarantined_count})"
        )


class _BatchMutationMixin(_BatchReadModelMixin):
    """Record append/quarantine behavior for Batch."""

    __slots__ = ()

    def add_record(
        self,
        data: BronzeRecord,
        entity_id: EntityID | None = None,
        content_hash: ContentHash | None = None,
    ) -> BatchRecord:
        """Add a single record to the batch.

        Args:
            data: Raw Bronze layer record dictionary to store.
            entity_id: Optional identifier for the entity represented by the record.
            content_hash: Optional content hash for deduplication tracking.

        Returns:
            The newly created BatchRecord appended to this batch.
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

    def add_records(self, records: list[BronzeRecord]) -> list[BatchRecord]:
        """Add multiple records to the batch.

        Args:
            records: List of raw Bronze layer record dictionaries to add.

        Returns:
            List of newly created BatchRecord objects in insertion order.
        """
        self._assert_open("add_records")
        return [self.add_record(data) for data in records]

    def quarantine_record(
        self,
        record: BatchRecord,
        error: str,
        error_code: str | None = None,
        *,
        quarantined_at: datetime,
    ) -> BatchRecord:
        """Mark an existing record as quarantined.

        Args:
            record: An existing BatchRecord that belongs to this batch.
            error: Human-readable description of the validation or processing error.
            error_code: Optional error classification code for downstream routing.
            quarantined_at: Explicit timestamp when the record was quarantined.

        Returns:
            Updated BatchRecord with quarantine status and error information.
        """
        self._assert_open("quarantine_record")
        if record not in self._records:
            raise ValueError("Record does not belong to this batch")

        quarantined = record.with_validation_error(error, error_code)
        index = self._records.index(record)
        self._records[index] = quarantined
        self._quarantined.append(quarantined)

        lifecycle.emit_record_quarantined(
            self._events,
            self._run_id,
            self._batch_id,
            record.entity_id,
            error_code,
            error,
            record.content_hash,
            quarantined_at,
        )
        return quarantined

    def _assert_open(self, operation: str) -> None:
        if not self._status.is_modifiable():
            raise InvalidStateError(
                f"Cannot {operation}: batch is in status {self._status.value}",
                current_state=self._status.value,
                attempted_operation=operation,
            )


class _BatchLifecycleMixin(_BatchReadModelMixin):
    """State transitions for Batch lifecycle."""

    __slots__ = ()

    def seal(self, sealed_at: datetime) -> None:
        """Seal the batch (OPEN -> SEALED).

        Args:
            sealed_at: Explicit seal timestamp.
        """
        self.seal_with_counts(
            record_count=self.record_count,
            valid_count=self.valid_count,
            quarantined_count=self.quarantined_count,
            sealed_at=sealed_at,
        )

    def seal_with_counts(
        self,
        *,
        record_count: int,
        valid_count: int,
        quarantined_count: int,
        sealed_at: datetime,
    ) -> None:
        """Seal the batch using runtime-computed transform result counts.

        Batch processing can filter or quarantine records outside the aggregate
        record collection. The transition still belongs to the aggregate; the
        runtime supplies the counts observed at the transform boundary.
        """
        self._status, self._sealed_at = lifecycle.seal(
            self._status,
            self._events,
            self._run_id,
            self._batch_id,
            record_count,
            valid_count,
            quarantined_count,
            sealed_at,
        )

    def mark_writing(self) -> None:
        """Mark batch as being written (SEALED -> WRITING)."""
        self._status = lifecycle.mark_writing(self._status)

    def mark_committed(self, layer: str, committed_at: datetime) -> None:
        """Mark batch as committed (WRITING -> COMMITTED).

        Args:
            layer: Medallion layer that successfully received the batch (e.g., 'bronze').
            committed_at: Explicit timestamp when the batch write completed.
        """
        self._status = lifecycle.mark_committed(
            self._status,
            self._events,
            self._run_id,
            self._batch_id,
            self.valid_count,
            layer,
            committed_at,
        )

    def mark_failed(
        self,
        layer: str,
        error: str,
        error_type: str | None = None,
        *,
        failed_at: datetime,
    ) -> None:
        """Mark batch write as failed (WRITING -> FAILED).

        Args:
            layer: Medallion layer where the write failure occurred.
            error: Human-readable error description.
            error_type: Optional error classification (e.g., exception class name).
            failed_at: Explicit timestamp when the batch failure occurred.
        """
        self._status = lifecycle.mark_failed(
            self._status,
            self._events,
            self._run_id,
            self._batch_id,
            layer,
            error,
            error_type,
            failed_at=failed_at,
        )
