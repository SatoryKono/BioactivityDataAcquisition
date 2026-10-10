"""Domain-event emission helpers for batch write paths."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from bioetl.application.core.batch_operation_errors import (
    OPERATION_ERRORS as DOMAIN_EVENT_EMISSION_ERRORS,
)
from bioetl.domain.aggregates.events import BatchFailed, BatchWritten, DomainEvent
from bioetl.domain.medallion import Layer
from bioetl.domain.types import BatchID, RunID

if TYPE_CHECKING:
    from bioetl.application.observability.domain_event_emitter import (
        DomainEventEmitterProtocol,
    )
    from bioetl.domain.ports import LoggerPort


@dataclass(frozen=True, slots=True)
class BatchWriteEventContext:
    """Stable event coordinates shared by one storage-layer write attempt."""

    emitter: DomainEventEmitterProtocol | None
    run_id: RunID | None
    batch_id: BatchID
    layer: str
    occurred_at: datetime
    logger: LoggerPort

    def emit_failed(self, error: Exception) -> None:
        """Publish one failed-write event for this layer attempt."""
        emit_batch_failed(
            emitter=self.emitter,
            run_id=self.run_id,
            batch_id=self.batch_id,
            layer=self.layer,
            error=error,
            occurred_at=self.occurred_at,
            logger=self.logger,
        )

    def emit_written(self, record_count: int) -> None:
        """Publish one successful-write event for this layer attempt."""
        emit_batch_written(
            emitter=self.emitter,
            run_id=self.run_id,
            batch_id=self.batch_id,
            layer=self.layer,
            record_count=record_count,
            occurred_at=self.occurred_at,
            logger=self.logger,
        )


def emit_domain_event(
    emitter: DomainEventEmitterProtocol | None,
    event: DomainEvent,
    *,
    logger: LoggerPort | None = None,
) -> None:
    """Best-effort publish; log emitter failures when a logger is available."""
    if emitter is None:
        return
    try:
        emitter.emit_domain_event(event)
    except DOMAIN_EVENT_EMISSION_ERRORS as error:
        if logger is not None:
            logger.warning(
                "domain_event_emit_failed",
                error=str(error),
                error_type=type(error).__name__,
                event_type=type(event).__name__,
            )


def emit_batch_written(
    *,
    emitter: DomainEventEmitterProtocol | None,
    run_id: RunID | None,
    batch_id: BatchID,
    layer: str,
    record_count: int,
    occurred_at: datetime,
    logger: LoggerPort | None = None,
) -> None:
    if run_id is None:
        return
    emit_domain_event(
        emitter,
        BatchWritten(
            occurred_at=occurred_at,
            run_id=run_id,
            batch_id=batch_id,
            layer=Layer(layer),
            record_count=record_count,
        ),
        logger=logger,
    )


def emit_batch_failed(
    *,
    emitter: DomainEventEmitterProtocol | None,
    run_id: RunID | None,
    batch_id: BatchID,
    layer: str,
    error: Exception,
    occurred_at: datetime,
    logger: LoggerPort | None = None,
) -> None:
    if run_id is None:
        return
    emit_domain_event(
        emitter,
        BatchFailed(
            occurred_at=occurred_at,
            run_id=run_id,
            batch_id=batch_id,
            layer=Layer(layer),
            error=str(error),
            error_type=type(error).__name__,
        ),
        logger=logger,
    )
