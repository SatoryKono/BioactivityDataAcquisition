"""Internal mixins for Batch aggregate behavior."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import TYPE_CHECKING

from bioetl.domain.aggregates.batch import (
    BatchRecord,
    BatchStatus,
    _BatchReadModelMixin,
)
from bioetl.domain.aggregates.events import (
    BatchFailed,
    BatchSealed,
    BatchWritten,
    RecordQuarantined,
)
from bioetl.domain.exceptions import InvalidStateError

if TYPE_CHECKING:
    from bioetl.domain.medallion import Layer
    from bioetl.domain.types import (
        BronzeRecord,
        ContentHash,
        EntityID,
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
                record_id=str(record.entity_id)
                if record.entity_id is not None
                else None,
                error_code=error_code,
                error_message=error,
                content_hash=record.content_hash,
            )
        )
        return quarantined

    def _owned_record(self, record: BatchRecord) -> tuple[int, BatchRecord]:
        """Return the position and owned record, rejecting foreign records."""
        position = record.index - self._start_index
        if position < 0 or position >= len(self._records):
            raise ValueError("Record does not belong to this batch")
        owned = self._records[position]
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
        """Mark batch as committed (WRITING -> COMMITTED).

        Args:
            layer: Medallion layer that successfully received the batch.
            committed_at: Explicit timestamp when the batch write completed.
        """
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
        """Mark batch write as failed (WRITING -> FAILED).

        Args:
            layer: Medallion layer where the write failure occurred.
            error: Human-readable error description.
            error_type: Optional error classification (e.g., exception class name).
            failed_at: Explicit timestamp when the batch failure occurred.
        """
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
