"""Batch aggregate types and compatibility Batch re-export (ADR-059)."""

from __future__ import annotations

import importlib
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

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


def __getattr__(name: str) -> object:
    if name == "Batch":
        module = importlib.import_module("bioetl.domain.aggregates._batch_aggregate")
        return module.Batch
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
