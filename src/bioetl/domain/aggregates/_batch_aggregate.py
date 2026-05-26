"""Batch aggregate root."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import bioetl.domain.aggregates._batch_lifecycle as lifecycle
from bioetl.domain.aggregates._batch_mixins import (
    _BatchLifecycleMixin,
    _BatchMutationMixin,
)
from bioetl.domain.aggregates._batch_record import BatchRecord
from bioetl.domain.aggregates._batch_status import BatchStatus

if TYPE_CHECKING:
    from bioetl.domain.aggregates.events import DomainEvent
from bioetl.domain.deterministic_identity import deterministic_uuid
from bioetl.domain.types import (
    BatchID,
    MetaDict,
    RunID,
)

__all__ = [
    "Batch",
]


class Batch(_BatchMutationMixin, _BatchLifecycleMixin):
    """Aggregate root for batch records."""

    __slots__ = ()

    def __init__(
        self,
        batch_id: BatchID,
        run_id: RunID,
        start_index: int = 0,
        *,
        created_at: datetime,
        metadata: MetaDict | None = None,
    ) -> None:
        """Initialise a new OPEN batch aggregate."""
        if start_index < 0:
            raise ValueError(f"start_index cannot be negative: {start_index}")

        self._batch_id = batch_id
        self._run_id = run_id
        self._status = BatchStatus.OPEN
        self._records: list[BatchRecord] = []
        self._quarantined: list[BatchRecord] = []
        self._start_index = start_index
        self._created_at = created_at
        self._sealed_at: datetime | None = None
        self._events: list[DomainEvent] = []
        self._metadata: MetaDict = metadata or {}

    @classmethod
    def create(
        cls,
        run_id: RunID,
        start_index: int = 0,
        *,
        created_at: datetime,
        metadata: MetaDict | None = None,
    ) -> Batch:
        """Create a new batch with a deterministic ID.

        Args:
            run_id: Pipeline run identifier that owns this batch.
            start_index: Index offset for the first record in the batch. Defaults to 0.
            created_at: Explicit timestamp when the batch was created.
            metadata: Optional key-value metadata to attach to the batch.

        Returns:
            New Batch instance with deterministic BatchID and OPEN status.
        """
        batch_id = BatchID(
            deterministic_uuid(
                "batch",
                {
                    "created_at": created_at,
                    "metadata": metadata or {},
                    "run_id": run_id,
                    "start_index": start_index,
                },
            )
        )
        batch = cls(
            batch_id=batch_id,
            run_id=run_id,
            start_index=start_index,
            created_at=created_at,
            metadata=metadata,
        )
        lifecycle.emit_batch_created(batch._events, batch._created_at, run_id, batch_id)
        return batch
