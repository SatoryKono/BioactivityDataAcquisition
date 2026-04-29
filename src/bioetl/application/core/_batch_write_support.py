"""Private write-path helpers for ``BatchProcessingSupportService``."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import TYPE_CHECKING

from bioetl.application.core.quarantine_manager import (
    DQQuarantineEntry,
    QuarantineManagerService,
)
from bioetl.domain.aggregates.events import BatchFailed, BatchWritten, DomainEvent
from bioetl.domain.exceptions import SchemaViolationError
from bioetl.domain.types import BatchID, ErrorType, RunID

if TYPE_CHECKING:
    from bioetl.application.core.batch_writer import BatchWriter
    from bioetl.application.observability.domain_event_emitter import (
        DomainEventEmitterProtocol,
    )
    from bioetl.domain.ports import LoggerPort
    from bioetl.domain.value_objects.bronze_result import BronzeWriteResult


def emit_domain_event(
    emitter: DomainEventEmitterProtocol | None,
    event: DomainEvent,
) -> None:
    """Best-effort publish of one typed domain event."""
    if emitter is None:
        return
    emitter.emit_domain_event(event)


def emit_batch_written(
    *,
    emitter: DomainEventEmitterProtocol | None,
    run_id: RunID | None,
    batch_id: BatchID,
    layer: str,
    record_count: int,
    occurred_at: datetime,
) -> None:
    """Publish a typed ``BatchWritten`` event when run context exists."""
    if run_id is None:
        return
    emit_domain_event(
        emitter,
        BatchWritten(
            occurred_at=occurred_at,
            run_id=run_id,
            batch_id=batch_id,
            layer=layer,
            record_count=record_count,
        ),
    )


def emit_batch_failed(
    *,
    emitter: DomainEventEmitterProtocol | None,
    run_id: RunID | None,
    batch_id: BatchID,
    layer: str,
    error: Exception,
    occurred_at: datetime,
) -> None:
    """Publish a typed ``BatchFailed`` event before bubbling the error."""
    if run_id is None:
        return
    emit_domain_event(
        emitter,
        BatchFailed(
            occurred_at=occurred_at,
            run_id=run_id,
            batch_id=batch_id,
            layer=layer,
            error=str(error),
            error_type=type(error).__name__,
        ),
    )


async def safe_write_layer(
    *,
    execute_with_span: Callable[..., Awaitable[object]],
    writer: BatchWriter,
    quarantine_manager: QuarantineManagerService,
    logger: LoggerPort,
    run_id: RunID | None,
    domain_event_emitter: DomainEventEmitterProtocol | None,
    layer: str,
    records: list[dict[str, object]],
    batch_id: BatchID,
    ingestion_ts: datetime,
    bronze_refs: list[BronzeWriteResult] | None,
    operation_errors: tuple[type[BaseException], ...],
) -> None:
    """Execute one layer write and quarantine schema-invalid outputs."""
    try:
        if layer == "silver":
            await execute_with_span(
                "write_silver",
                writer.write_silver(
                    records,
                    batch_id,
                    ingestion_ts,
                    bronze_refs=bronze_refs,
                ),
                batch_id,
                len(records),
                on_error=lambda error: writer.log_and_track_write_error(
                    "silver",
                    error,
                    batch_id,
                    record_count=len(records),
                ),
            )
        else:
            await execute_with_span(
                "write_gold",
                writer.write_gold(records),
                batch_id,
                len(records),
                on_error=lambda error: writer.log_and_track_write_error(
                    "gold",
                    error,
                    batch_id,
                    record_count=len(records),
                ),
            )
        writer._batch_metrics.track_batch_written(stage=layer, count=len(records))
        emit_batch_written(
            emitter=domain_event_emitter,
            run_id=run_id,
            batch_id=batch_id,
            layer=layer,
            record_count=len(records),
            occurred_at=ingestion_ts,
        )
    except SchemaViolationError as error:
        writer._batch_metrics.track_batch_failed(stage=layer, count=len(records))
        emit_batch_failed(
            emitter=domain_event_emitter,
            run_id=run_id,
            batch_id=batch_id,
            layer=layer,
            error=error,
            occurred_at=ingestion_ts,
        )
        logger.warning(
            "schema_violation_quarantined",
            layer=layer,
            errors=error.errors,
        )
        await quarantine_manager.quarantine_records(
            [
                DQQuarantineEntry(
                    record=record,
                    error_type=ErrorType.SCHEMA_VIOLATION,
                    error_details=f"Schema violation in {layer}: {error.errors}",
                )
                for record in records
            ],
            batch_id,
            ingestion_ts=ingestion_ts,
        )
    except operation_errors as error:
        if isinstance(error, Exception):
            writer._batch_metrics.track_batch_failed(stage=layer, count=len(records))
            emit_batch_failed(
                emitter=domain_event_emitter,
                run_id=run_id,
                batch_id=batch_id,
                layer=layer,
                error=error,
                occurred_at=ingestion_ts,
            )
        raise
