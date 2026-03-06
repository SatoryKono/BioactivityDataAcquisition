"""Batch Aggregate Root.

Invariants:
    1. All records in a batch have the same batch_id
    2. Records cannot be added after the batch is sealed
    3. batch_id is unique and immutable
    4. Record indices are sequential starting from start_index
    5. Quarantined records are tracked separately from valid records
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from bioetl.domain.aggregates import _batch_lifecycle as lifecycle
from bioetl.domain.aggregates._batch_record import BatchRecord
from bioetl.domain.aggregates._batch_status import BatchStatus
from bioetl.domain.exceptions import InvalidStateError

if TYPE_CHECKING:
    from bioetl.domain.aggregates.events import DomainEvent
from bioetl.domain.types import (
    BatchID,
    BronzeRecord,
    ContentHash,
    EntityID,
    MetaDict,
    RunID,
)

__all__ = [
    "Batch",
]


class Batch:
    """Aggregate Root for a collection of records.

    Lifecycle: OPEN -> SEALED -> WRITING -> COMMITTED | FAILED.
    State transitions and event emission delegated to ``_batch_lifecycle``.
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
        metadata: MetaDict | None = None,
    ) -> None:
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
        self._events: list[DomainEvent] = []
        self._metadata: MetaDict = metadata or {}

    @classmethod
    def create(
        cls,
        run_id: RunID,
        start_index: int = 0,
        metadata: MetaDict | None = None,
    ) -> Batch:
        """Factory method to create a new batch with generated ID."""
        from uuid import uuid4

        batch_id = BatchID(uuid4())
        batch = cls(
            batch_id=batch_id,
            run_id=run_id,
            start_index=start_index,
            metadata=metadata,
        )
        lifecycle.emit_batch_created(batch._events, batch._created_at, run_id, batch_id)
        return batch

    # ── Read-only properties ──────────────────────────────────────────────

    @property
    def batch_id(self) -> BatchID:
        return self._batch_id

    @property
    def run_id(self) -> RunID:
        return self._run_id

    @property
    def status(self) -> BatchStatus:
        return self._status

    @property
    def records(self) -> tuple[BatchRecord, ...]:
        return tuple(r for r in self._records if r.is_valid)

    @property
    def all_records(self) -> tuple[BatchRecord, ...]:
        return tuple(self._records)

    @property
    def quarantined_records(self) -> tuple[BatchRecord, ...]:
        return tuple(self._quarantined)

    @property
    def record_count(self) -> int:
        return len(self._records)

    @property
    def valid_count(self) -> int:
        return sum(1 for r in self._records if r.is_valid)

    @property
    def quarantined_count(self) -> int:
        return len(self._quarantined)

    @property
    def next_index(self) -> int:
        return self._start_index + len(self._records)

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def sealed_at(self) -> datetime | None:
        return self._sealed_at

    @property
    def metadata(self) -> MetaDict:
        return self._metadata.copy()

    # ── Record management ─────────────────────────────────────────────────

    def add_record(
        self,
        data: BronzeRecord,
        entity_id: EntityID | None = None,
        content_hash: ContentHash | None = None,
    ) -> BatchRecord:
        """Add a record to the batch.

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
        records: list[BronzeRecord],
    ) -> list[BatchRecord]:
        """Add multiple records to the batch.

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

        Raises:
            InvalidStateError: If batch is not OPEN.
            ValueError: If record is not in this batch.
        """
        self._assert_open("quarantine_record")

        if record not in self._records:
            raise ValueError("Record does not belong to this batch")

        quarantined = record.with_validation_error(error, error_code)
        idx = self._records.index(record)
        self._records[idx] = quarantined
        self._quarantined.append(quarantined)

        lifecycle.emit_record_quarantined(
            self._events,
            self._run_id,
            self._batch_id,
            record.entity_id,
            error_code,
            error,
            record.content_hash,
        )
        return quarantined

    # ── Lifecycle transitions ─────────────────────────────────────────────

    def seal(self, sealed_at: datetime | None = None) -> None:
        """Seal the batch (OPEN -> SEALED)."""
        self._status, self._sealed_at = lifecycle.seal(
            self._status,
            self._events,
            self._run_id,
            self._batch_id,
            self.record_count,
            self.valid_count,
            self.quarantined_count,
            sealed_at,
        )

    def mark_writing(self) -> None:
        """Mark batch as being written (SEALED -> WRITING)."""
        self._status = lifecycle.mark_writing(self._status)

    def mark_committed(self, layer: str) -> None:
        """Mark batch as committed (WRITING -> COMMITTED)."""
        self._status = lifecycle.mark_committed(
            self._status,
            self._events,
            self._run_id,
            self._batch_id,
            self.valid_count,
            layer,
        )

    def mark_failed(
        self, layer: str, error: str, error_type: str | None = None
    ) -> None:
        """Mark batch write as failed (WRITING -> FAILED)."""
        self._status = lifecycle.mark_failed(
            self._status,
            self._events,
            self._run_id,
            self._batch_id,
            layer,
            error,
            error_type,
        )

    # ── Domain events ─────────────────────────────────────────────────────

    def collect_events(self) -> list[DomainEvent]:
        """Collect and clear accumulated domain events."""
        events = self._events.copy()
        self._events.clear()
        return events

    # ── Private helpers ───────────────────────────────────────────────────

    def _assert_open(self, operation: str) -> None:
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
