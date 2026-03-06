"""Batch lifecycle transitions and event emission.

Extracted from Batch aggregate root to reduce class size (RF-011).
All event imports are centralized here — no lazy imports needed.

Functions are called by Batch methods to perform state validation,
state transitions, and domain event emission.
"""

from __future__ import annotations

from datetime import UTC, datetime
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
    from bioetl.domain.types import BatchID, ContentHash, EntityID, RunID

__all__: list[str] = []


def emit_batch_created(
    events: list[DomainEvent],
    occurred_at: datetime,
    run_id: RunID,
    batch_id: BatchID,
) -> None:
    """Append a BatchCreated event."""
    events.append(
        BatchCreated(
            occurred_at=occurred_at,
            run_id=run_id,
            batch_id=batch_id,
            record_count=0,
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
    sealed_at: datetime | None = None,
) -> tuple[BatchStatus, datetime]:
    """Validate and perform OPEN -> SEALED transition.

    Returns:
        Tuple of (BatchStatus.SEALED, sealed_at timestamp).
    """
    if not status.is_modifiable():
        raise InvalidStateError(
            f"Cannot seal: batch is in status {status.value}",
            current_state=status.value,
            attempted_operation="seal",
        )
    ts = sealed_at or datetime.now(UTC)
    events.append(
        BatchSealed(
            occurred_at=ts,
            run_id=run_id,
            batch_id=batch_id,
            record_count=record_count,
            valid_count=valid_count,
            quarantined_count=quarantined_count,
        )
    )
    return BatchStatus.SEALED, ts


def mark_writing(status: BatchStatus) -> BatchStatus:
    """Validate and perform SEALED -> WRITING transition.

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
    layer: str,
) -> BatchStatus:
    """Validate and perform WRITING -> COMMITTED transition.

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
            occurred_at=datetime.now(UTC),
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
    layer: str,
    error: str,
    error_type: str | None = None,
) -> BatchStatus:
    """Validate and perform WRITING -> FAILED transition.

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
            occurred_at=datetime.now(UTC),
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
) -> None:
    """Append a RecordQuarantined event."""
    events.append(
        RecordQuarantined(
            occurred_at=datetime.now(UTC),
            run_id=run_id,
            batch_id=batch_id,
            record_id=str(entity_id) if entity_id else None,
            error_code=error_code,
            error_message=error,
            content_hash=content_hash,
        )
    )
