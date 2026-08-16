# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
"""Typed private attribute contract shared by Batch aggregate mixins."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from bioetl.domain.aggregates._batch_record import BatchRecord
from bioetl.domain.aggregates._batch_status import BatchStatus

if TYPE_CHECKING:
    from bioetl.domain.aggregates.events import DomainEvent
    from bioetl.domain.types import BatchID, MetaDict, RunID


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


__all__ = ["_BatchAttrs"]
