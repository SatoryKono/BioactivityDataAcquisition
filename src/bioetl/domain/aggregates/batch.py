"""Batch aggregate types and compatibility Batch re-export (ADR-059)."""

from __future__ import annotations

import importlib
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from bioetl.domain.aggregates.events import RecordQuarantined
from bioetl.domain.exceptions import InvalidStateError
from bioetl.domain.immutability import deep_freeze_json
from bioetl.domain.types import (
    BronzeRecord,
    ContentHash,
    EntityID,
)

if TYPE_CHECKING:
    from bioetl.domain.aggregates.events import DomainEvent
    from bioetl.domain.types import BatchID, MetaDict, RunID

__all__ = [
    "BatchRecord",
    "BatchStatus",
    "_BatchAttrs",
]


class BatchStatus(StrEnum):
    """Status of a batch."""

    OPEN = "open"
    SEALED = "sealed"
    WRITING = "writing"
    COMMITTED = "committed"
    FAILED = "failed"

    def is_modifiable(self) -> bool:
        """Check if records can still be added."""
        return self == BatchStatus.OPEN


@dataclass(frozen=True, slots=True)
class BatchRecord:
    """Immutable value object representing a record in a batch."""

    index: int
    entity_id: EntityID | None
    content_hash: ContentHash | None
    data: BronzeRecord
    is_valid: bool = True
    error: str | None = None
    error_code: str | None = None

    def __post_init__(self) -> None:
        """Validate record invariants."""
        if self.index < 0:
            raise ValueError(f"Record index cannot be negative: {self.index}")
        if not self.is_valid and not self.error:
            raise ValueError("Invalid record must have an error message")
        object.__setattr__(self, "data", deep_freeze_json(self.data))

    def with_validation_error(
        self, error: str, error_code: str | None = None
    ) -> BatchRecord:
        """Create a new BatchRecord marked as invalid."""
        return BatchRecord(
            index=self.index,
            entity_id=self.entity_id,
            content_hash=self.content_hash,
            data=self.data,
            is_valid=False,
            error=error,
            error_code=error_code,
        )


class _BatchAttrs:
    """Typed private attributes shared by Batch mixins."""

    __slots__ = (
        "_batch_id",
        "_created_at",
        "_events",
        "_metadata",
        "_quarantined",
        "_records",
        "_run_id",
        "_sealed_at",
        "_sealed_valid_count",
        "_start_index",
        "_status",
    )

    _batch_id: BatchID  # pyright: ignore[reportUninitializedInstanceVariable]
    _run_id: RunID  # pyright: ignore[reportUninitializedInstanceVariable]
    _status: BatchStatus  # pyright: ignore[reportUninitializedInstanceVariable]
    _records: list[BatchRecord]  # pyright: ignore[reportUninitializedInstanceVariable]
    _quarantined: list[BatchRecord]  # pyright: ignore[reportUninitializedInstanceVariable]
    _start_index: int  # pyright: ignore[reportUninitializedInstanceVariable]
    _created_at: datetime  # pyright: ignore[reportUninitializedInstanceVariable]
    _sealed_at: datetime | None  # pyright: ignore[reportUninitializedInstanceVariable]
    _sealed_valid_count: int | None  # pyright: ignore[reportUninitializedInstanceVariable]
    _events: list[DomainEvent]  # pyright: ignore[reportUninitializedInstanceVariable]
    _metadata: MetaDict  # pyright: ignore[reportUninitializedInstanceVariable]


class _BatchReadModelMixin(_BatchAttrs):
    """Read model projections and event collection."""

    __slots__ = ()

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
        return tuple(record for record in self._records if record.is_valid)

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
        return sum(1 for record in self._records if record.is_valid)

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
        return deepcopy(self._metadata)

    def collect_events(self) -> list[DomainEvent]:
        events = self._events.copy()
        self._events.clear()
        return events

    def __repr__(self) -> str:
        return (
            f"Batch(batch_id={self._batch_id!r}, "
            f"status={self._status.value!r}, records={self.record_count}, "
            f"valid={self.valid_count}, quarantined={self.quarantined_count})"
        )


def _owned_record_id(record: BatchRecord) -> str | None:
    entity_id = record.entity_id
    if entity_id is None:
        return None
    return str(entity_id)


class _BatchMutationMixin(_BatchReadModelMixin):
    """Record append/quarantine behavior for Batch."""

    __slots__ = ()

    def add_record(
        self,
        data: BronzeRecord,
        entity_id: EntityID | None = None,
        content_hash: ContentHash | None = None,
    ) -> BatchRecord:
        """Append one Bronze record and return its aggregate representation."""
        self._assert_open("add_record")
        record = BatchRecord(
            index=self.next_index,
            entity_id=entity_id,
            content_hash=content_hash,
            data=deepcopy(data),
            is_valid=True,
        )
        self._records.append(record)
        return record

    def add_records(self, records: list[BronzeRecord]) -> list[BatchRecord]:
        """Append Bronze records in input order."""
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
        """Mark a batch-owned record as quarantined and emit its event once."""
        self._assert_open("quarantine_record")
        position, owned = self._owned_record(record)
        # Idempotent quarantine: already-invalid owned records must not
        # duplicate the quarantine projection or RecordQuarantined events.
        if not owned.is_valid:
            return owned

        quarantined = record.with_validation_error(error, error_code)
        self._records[position] = quarantined
        self._quarantined.append(quarantined)

        self._events.append(
            RecordQuarantined(
                occurred_at=quarantined_at,
                run_id=self._run_id,
                batch_id=self._batch_id,
                record_id=_owned_record_id(record),
                error_code=error_code,
                error_message=error,
                content_hash=record.content_hash,
            )
        )
        return quarantined

    def _owned_record(self, record: BatchRecord) -> tuple[int, BatchRecord]:
        """Return the local position and record, rejecting foreign records."""
        position = record.index - self._start_index
        if position < 0 or position >= len(self._records):
            raise ValueError("Record does not belong to this batch")
        owned = self._records[position]
        # Reject foreign records that only share an index with a batch-owned row.
        if owned != record:
            raise ValueError("Record does not belong to this batch")
        return position, owned

    def _assert_open(self, operation: str) -> None:
        if not self._status.is_modifiable():
            raise InvalidStateError(
                f"Cannot {operation}: batch is in status {self._status.value}",
                current_state=self._status.value,
                attempted_operation=operation,
            )


def __getattr__(name: str) -> object:
    if name == "Batch":
        module = importlib.import_module("bioetl.domain.aggregates._batch_aggregate")
        return module.Batch
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
