"""Batch lifecycle transitions and event emission.

Extracted from Batch aggregate root to reduce class size (RF-011).
All event imports are centralized here — no lazy imports needed.

Functions are called by Batch methods to perform state validation,
state transitions, and domain event emission.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from bioetl.domain.aggregates._batch_status import BatchStatus
from bioetl.domain.aggregates.events import (
    BatchCreated,
    BatchFailed,
    BatchSealed,
    BatchWritten,
    RecordQuarantined,
)
from bioetl.domain.exceptions import InvalidStateError

if TYPE_CHECKING:
    from bioetl.domain.aggregates.events import DomainEvent
    from bioetl.domain.medallion import Layer
    from bioetl.domain.types import BatchID, ContentHash, EntityID, RunID

__all__: list[str] = []


def emit_batch_created(
    events: list[DomainEvent],
    occurred_at: datetime,
    run_id: RunID,
    batch_id: BatchID,
    record_count: int = 0,
) -> None:
    """Append a BatchCreated event.

    Args:
        events: Mutable event list on the aggregate to append the event to.
        occurred_at: Timestamp when the batch was created.
        run_id: Pipeline run identifier that owns the batch.
        batch_id: Unique identifier assigned to the new batch.
        record_count: Number of records already associated with the batch.
    """
    events.append(
        BatchCreated(
            occurred_at=occurred_at,
            run_id=run_id,
            batch_id=batch_id,
            record_count=record_count,
        )
    )


def seal(
    status: BatchStatus,
    events: list[DomainEvent],
    run_id: RunID,
    batch_id: BatchID,
    record_count: int,
    valid_count: int,
    quarantined_count: int,
    sealed_at: datetime,
) -> tuple[BatchStatus, datetime]:
    """Validate and perform OPEN -> SEALED transition.

    Args:
        status: Current batch status, must be OPEN.
        events: Mutable event list to append the BatchSealed event to.
        run_id: Pipeline run identifier.
        batch_id: Batch identifier.
        record_count: Total number of records in the batch.
        valid_count: Number of valid (non-quarantined) records.
        quarantined_count: Number of quarantined records.
        sealed_at: Explicit seal timestamp.

    Returns:
        Tuple of (BatchStatus.SEALED, sealed_at timestamp).
    """
    if not status.is_modifiable():
        raise InvalidStateError(
            f"Cannot seal: batch is in status {status.value}",
            current_state=status.value,
            attempted_operation="seal",
        )
    events.append(
        BatchSealed(
            occurred_at=sealed_at,
            run_id=run_id,
            batch_id=batch_id,
            record_count=record_count,
            valid_count=valid_count,
            quarantined_count=quarantined_count,
        )
    )
    return BatchStatus.SEALED, sealed_at


def mark_writing(status: BatchStatus) -> BatchStatus:
    """Validate and perform SEALED -> WRITING transition.

    Args:
        status: Current batch status, must be SEALED.

    Returns:
        BatchStatus.WRITING after successful transition.
    """
    if status != BatchStatus.SEALED:
        raise InvalidStateError(
            f"Cannot mark as writing: batch is in status {status.value}",
            current_state=status.value,
            attempted_operation="mark_writing",
        )
    return BatchStatus.WRITING


def mark_committed(
    status: BatchStatus,
    events: list[DomainEvent],
    run_id: RunID,
    batch_id: BatchID,
    valid_count: int,
    layer: Layer,
    committed_at: datetime,
) -> BatchStatus:
    """Validate and perform WRITING -> COMMITTED transition.

    Args:
        status: Current batch status, must be WRITING.
        events: Mutable event list to append the BatchWritten event to.
        run_id: Pipeline run identifier.
        batch_id: Batch identifier.
        valid_count: Number of valid records successfully written.
        layer: Medallion layer that successfully received the batch.
        committed_at: Explicit timestamp when the batch write completed.

    Returns:
        BatchStatus.COMMITTED after successful transition.
    """
    if status != BatchStatus.WRITING:
        raise InvalidStateError(
            f"Cannot commit: batch is in status {status.value}",
            current_state=status.value,
            attempted_operation="mark_committed",
        )
    events.append(
        BatchWritten(
            occurred_at=committed_at,
            run_id=run_id,
            batch_id=batch_id,
            layer=layer,
            record_count=valid_count,
        )
    )
    return BatchStatus.COMMITTED


def mark_failed(
    status: BatchStatus,
    events: list[DomainEvent],
    run_id: RunID,
    batch_id: BatchID,
    layer: Layer,
    error: str,
    error_type: str | None = None,
    *,
    failed_at: datetime,
) -> BatchStatus:
    """Validate and perform WRITING -> FAILED transition.

    Args:
        status: Current batch status, must be WRITING.
        events: Mutable event list to append the BatchFailed event to.
        run_id: Pipeline run identifier.
        batch_id: Batch identifier.
        layer: Medallion layer where failure occurred (e.g., 'bronze').
        error: Human-readable error message describing the failure.
        error_type: Optional error classification (e.g., exception class name).
        failed_at: Explicit timestamp when the batch failure occurred.

    Returns:
        BatchStatus.FAILED after recording the failure event.
    """
    if status != BatchStatus.WRITING:
        raise InvalidStateError(
            f"Cannot fail: batch is in status {status.value}",
            current_state=status.value,
            attempted_operation="mark_failed",
        )
    events.append(
        BatchFailed(
            occurred_at=failed_at,
            run_id=run_id,
            batch_id=batch_id,
            layer=layer,
            error=error,
            error_type=error_type,
        )
    )
    return BatchStatus.FAILED


def emit_record_quarantined(
    events: list[DomainEvent],
    run_id: RunID,
    batch_id: BatchID,
    entity_id: EntityID | None,
    error_code: str | None,
    error: str,
    content_hash: ContentHash | None,
    occurred_at: datetime,
) -> None:
    """Append a RecordQuarantined event.

    Args:
        events: Mutable event list on the aggregate to append the event to.
        run_id: Pipeline run identifier.
        batch_id: Batch that contains the quarantined record.
        entity_id: Optional entity identifier of the failed record.
        error_code: Optional classification code for the error.
        error: Human-readable error message.
        content_hash: Optional content hash of the failed record for deduplication.
        occurred_at: Explicit timestamp when the record was quarantined.
    """
    events.append(
        RecordQuarantined(
            occurred_at=occurred_at,
            run_id=run_id,
            batch_id=batch_id,
            record_id=str(entity_id) if entity_id else None,
            error_code=error_code,
            error_message=error,
            content_hash=content_hash,
        )
    )
