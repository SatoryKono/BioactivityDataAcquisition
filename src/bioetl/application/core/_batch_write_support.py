"""Private write-path helpers for ``BatchProcessingSupportService``."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import TYPE_CHECKING

from bioetl.application.core.quarantine_manager import (
    DQQuarantineEntry,
    QuarantineRuntimeService,
)
from bioetl.domain.aggregates.events import BatchFailed, BatchWritten, DomainEvent
from bioetl.domain.exceptions import SchemaViolationError
from bioetl.domain.medallion import Layer
from bioetl.domain.types import BatchID, ErrorType, RunID

if TYPE_CHECKING:
    from bioetl.application.core.batch_writer import BatchWriter
    from bioetl.application.observability.domain_event_emitter import (
        DomainEventEmitterProtocol,
    )
    from bioetl.domain.ports import LoggerPort
    from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
    from bioetl.domain.value_objects.silver_result import SilverWriteResult


def emit_domain_event(
    emitter: DomainEventEmitterProtocol | None,
    event: DomainEvent,
    *,
    logger: LoggerPort | None = None,
) -> None:
    """Best-effort publish of one typed domain event.

    Emitter failures must not break the write path; log when a logger is available.
    """
    if emitter is None:
        return
    try:
        emitter.emit_domain_event(event)
    except Exception as error:
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
    """Publish a typed ``BatchWritten`` event when run context exists."""
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
    """Publish a typed ``BatchFailed`` event before bubbling the error."""
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


async def _execute_layer_write(
    *,
    execute_with_span: Callable[..., Awaitable[object]],
    writer: BatchWriter,
    layer: str,
    records: list[dict[str, object]],
    batch_id: BatchID,
    ingestion_ts: datetime,
    bronze_refs: list[BronzeWriteResult] | None,
    silver_refs: list[SilverWriteResult] | None,
) -> object:
    """Execute the layer-specific writer call inside its tracing span."""
    if layer == "silver":
        operation = writer.write_silver(
            records,
            batch_id,
            ingestion_ts,
            bronze_refs=bronze_refs,
        )
    else:
        operation = writer.write_gold(records, silver_refs=silver_refs)
    return await execute_with_span(
        f"write_{layer}",
        operation,
        batch_id,
        len(records),
        on_error=lambda error: writer.log_and_track_write_error(
            layer,
            error,
            batch_id,
            record_count=len(records),
        ),
    )


async def safe_write_layer(
    *,
    execute_with_span: Callable[..., Awaitable[object]],
    writer: BatchWriter,
    quarantine_manager: QuarantineRuntimeService,
    logger: LoggerPort,
    run_id: RunID | None,
    domain_event_emitter: DomainEventEmitterProtocol | None,
    layer: str,
    records: list[dict[str, object]],
    batch_id: BatchID,
    ingestion_ts: datetime,
    bronze_refs: list[BronzeWriteResult] | None,
    silver_refs: list[SilverWriteResult] | None = None,
    operation_errors: tuple[type[BaseException], ...],
) -> object | None:
    """Execute one layer write and quarantine schema-invalid outputs."""
    if layer not in {"silver", "gold"}:
        raise ValueError(
            f"safe_write_layer supports only 'silver' or 'gold' layers, got {layer!r}"
        )
    try:
        write_result = await _execute_layer_write(
            execute_with_span=execute_with_span,
            writer=writer,
            layer=layer,
            records=records,
            batch_id=batch_id,
            ingestion_ts=ingestion_ts,
            bronze_refs=bronze_refs,
            silver_refs=silver_refs,
        )
        writer.track_batch_written(stage=layer, count=len(records))
        emit_batch_written(
            emitter=domain_event_emitter,
            run_id=run_id,
            batch_id=batch_id,
            layer=layer,
            record_count=len(records),
            occurred_at=ingestion_ts,
            logger=logger,
        )
        return write_result
    except SchemaViolationError as error:
        await _quarantine_schema_violation(
            writer=writer,
            quarantine_manager=quarantine_manager,
            logger=logger,
            domain_event_emitter=domain_event_emitter,
            run_id=run_id,
            layer=layer,
            records=records,
            batch_id=batch_id,
            ingestion_ts=ingestion_ts,
            error=error,
        )
        return None
    except operation_errors as error:
        if isinstance(error, Exception):
            writer.track_batch_failed(stage=layer, count=len(records))
            emit_batch_failed(
                emitter=domain_event_emitter,
                run_id=run_id,
                batch_id=batch_id,
                layer=layer,
                error=error,
                occurred_at=ingestion_ts,
                logger=logger,
            )
        raise


async def _quarantine_schema_violation(
    *,
    writer: BatchWriter,
    quarantine_manager: QuarantineRuntimeService,
    logger: LoggerPort,
    domain_event_emitter: DomainEventEmitterProtocol | None,
    run_id: RunID | None,
    layer: str,
    records: list[dict[str, object]],
    batch_id: BatchID,
    ingestion_ts: datetime,
    error: SchemaViolationError,
) -> None:
    """Track failure metrics and quarantine schema-invalid records."""
    writer.track_batch_failed(stage=layer, count=len(records))
    emit_batch_failed(
        emitter=domain_event_emitter,
        run_id=run_id,
        batch_id=batch_id,
        layer=layer,
        error=error,
        occurred_at=ingestion_ts,
        logger=logger,
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
