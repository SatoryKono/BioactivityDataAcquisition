# pyright: reportUninitializedInstanceVariable=false
# pyright: reportAttributeAccessIssue=false
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
        "_start_index",
        "_status",
    )

    _batch_id: BatchID
    _run_id: RunID
    _status: BatchStatus
    _records: list[BatchRecord]
    _quarantined: list[BatchRecord]
    _start_index: int
    _created_at: datetime
    _sealed_at: datetime | None
    _events: list[DomainEvent]
    _metadata: MetaDict


__all__ = ["_BatchAttrs"]
