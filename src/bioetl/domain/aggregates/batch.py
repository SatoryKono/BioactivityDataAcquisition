"""Batch aggregate types and compatibility Batch re-export (ADR-059)."""

from __future__ import annotations

import importlib
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


def __getattr__(name: str) -> object:
    if name == "Batch":
        module = importlib.import_module("bioetl.domain.aggregates._batch_aggregate")
        return getattr(module, "Batch")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
