"""Batch aggregate root."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import TYPE_CHECKING

from bioetl.domain.aggregates.batch import (
    BatchRecord,
    BatchStatus,
    _BatchMutationMixin,
)
from bioetl.domain.aggregates.events import (
    BatchCreated,
    BatchFailed,
    BatchSealed,
    BatchWritten,
)
from bioetl.domain.deterministic_identity import deterministic_uuid
from bioetl.domain.exceptions import InvalidStateError
from bioetl.domain.types import (
    BatchID,
    BronzeRecord,
    MetaDict,
    RunID,
)

if TYPE_CHECKING:
    from bioetl.domain.aggregates.events import DomainEvent
    from bioetl.domain.medallion import Layer

__all__ = [
    "Batch",
]


class _BatchLifecycleMixin(_BatchMutationMixin):
    """State transitions for Batch lifecycle."""

    __slots__ = ()

    def seal(self, sealed_at: datetime) -> None:
        """Seal the batch (OPEN -> SEALED)."""
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

        Counts must be non-negative and satisfy
        valid_count + quarantined_count == record_count.
        """
        self._validate_seal_counts(record_count, valid_count, quarantined_count)
        if not self._status.is_modifiable():
            raise InvalidStateError(
                f"Cannot seal: batch is in status {self._status.value}",
                current_state=self._status.value,
                attempted_operation="seal",
            )
        self._events.append(
            BatchSealed(
                occurred_at=sealed_at,
                run_id=self._run_id,
                batch_id=self._batch_id,
                record_count=record_count,
                valid_count=valid_count,
                quarantined_count=quarantined_count,
            )
        )
        self._status, self._sealed_at = BatchStatus.SEALED, sealed_at
        self._sealed_valid_count = valid_count

    @staticmethod
    def _validate_seal_counts(
        record_count: int,
        valid_count: int,
        quarantined_count: int,
    ) -> None:
        """Validate transform-result counts before sealing."""
        if record_count < 0 or valid_count < 0 or quarantined_count < 0:
            raise ValueError(
                "seal counts must be non-negative: "
                f"record_count={record_count}, valid_count={valid_count}, "
                f"quarantined_count={quarantined_count}"
            )
        if valid_count + quarantined_count != record_count:
            raise ValueError(
                "seal counts are inconsistent: "
                f"valid_count ({valid_count}) + quarantined_count "
                f"({quarantined_count}) != record_count ({record_count})"
            )

    def mark_writing(self) -> None:
        """Mark batch as being written (SEALED -> WRITING)."""
        if self._status != BatchStatus.SEALED:
            raise InvalidStateError(
                f"Cannot mark as writing: batch is in status {self._status.value}",
                current_state=self._status.value,
                attempted_operation="mark_writing",
            )
        self._status = BatchStatus.WRITING

    def mark_committed(self, layer: Layer, committed_at: datetime) -> None:
        """Mark batch as committed (WRITING -> COMMITTED)."""
        sealed_valid_count = (
            self._sealed_valid_count
            if self._sealed_valid_count is not None
            else self.valid_count
        )
        if self._status != BatchStatus.WRITING:
            raise InvalidStateError(
                f"Cannot commit: batch is in status {self._status.value}",
                current_state=self._status.value,
                attempted_operation="mark_committed",
            )
        self._events.append(
            BatchWritten(
                occurred_at=committed_at,
                run_id=self._run_id,
                batch_id=self._batch_id,
                layer=layer,
                record_count=sealed_valid_count,
            )
        )
        self._status = BatchStatus.COMMITTED

    def mark_failed(
        self,
        layer: Layer,
        error: str,
        error_type: str | None = None,
        *,
        failed_at: datetime,
    ) -> None:
        """Mark batch write as failed (WRITING -> FAILED)."""
        if self._status != BatchStatus.WRITING:
            raise InvalidStateError(
                f"Cannot fail: batch is in status {self._status.value}",
                current_state=self._status.value,
                attempted_operation="mark_failed",
            )
        self._events.append(
            BatchFailed(
                occurred_at=failed_at,
                run_id=self._run_id,
                batch_id=self._batch_id,
                layer=layer,
                error=error,
                error_type=error_type,
            )
        )
        self._status = BatchStatus.FAILED


class Batch(_BatchLifecycleMixin):
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
        self._sealed_valid_count: int | None = None
        self._events: list[DomainEvent] = []
        self._metadata: MetaDict = deepcopy(metadata) if metadata is not None else {}

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
        batch._events.append(
            BatchCreated(
                occurred_at=batch._created_at,
                run_id=run_id,
                batch_id=batch_id,
                record_count=0,
            )
        )
        return batch

    @classmethod
    def open_with_id(
        cls,
        *,
        batch_id: BatchID,
        run_id: RunID,
        records: list[BronzeRecord],
        start_index: int = 0,
        created_at: datetime,
        metadata: MetaDict | None = None,
    ) -> Batch:
        """Open a batch around an externally assigned identifier.

        Runtime processing owns batch ID generation through ``BatchIdGeneratorPort``.
        This constructor keeps that identity seam while ensuring lifecycle events
        are still emitted by the aggregate boundary rather than application code.
        """
        batch = cls(
            batch_id=batch_id,
            run_id=run_id,
            start_index=start_index,
            created_at=created_at,
            metadata=metadata,
        )
        batch.add_records(records)
        batch._events.append(
            BatchCreated(
                occurred_at=batch._created_at,
                run_id=run_id,
                batch_id=batch_id,
                record_count=batch.record_count,
            )
        )
        return batch
