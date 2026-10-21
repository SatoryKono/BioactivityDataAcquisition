"""Private write-path helpers for ``BatchProcessingSupportService``."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import TYPE_CHECKING

from bioetl.application.core._batch_write_events import (
    BatchWriteEventContext,
    emit_batch_failed,
    emit_batch_written,
    emit_domain_event,
)
from bioetl.application.core._batch_write_schema_quarantine import (
    quarantine_schema_violation,
)
from bioetl.application.core._gold_outcome_disposition import (
    bind_gold_quarantine_batch_if_supported,
    consume_gold_outcome_quarantine_count,
)
from bioetl.application.services.batch_processing.write_collaborators import (
    LayerWriteContext,
    LayerWriteOutcome,
    WriteLayerStatus,
)
from bioetl.domain.exceptions import SchemaViolationError
from bioetl.domain.exceptions.gold_write import GoldWriteFailure
from bioetl.domain.types import BatchID
from bioetl.domain.types.gold_contracts import require_complete_gold_receipt

if TYPE_CHECKING:
    from bioetl.application.core.batch_writer import BatchWriter
    from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
    from bioetl.domain.value_objects.silver_result import SilverWriteResult

__all__ = [
    "LayerWriteContext",
    "LayerWriteOutcome",
    "WriteLayerStatus",
    "emit_batch_failed",
    "emit_batch_written",
    "emit_domain_event",
    "safe_write_layer",
]


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
    operation: Awaitable[object]
    if layer == "silver":
        operation = writer.write_silver(
            records,
            batch_id,
            ingestion_ts,
            bronze_refs=bronze_refs,
        )
    else:
        bind_gold_quarantine_batch_if_supported(writer, batch_id)
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
    context: LayerWriteContext,
    layer: str,
    records: list[dict[str, object]],
    batch_id: BatchID,
    ingestion_ts: datetime,
    bronze_refs: list[BronzeWriteResult] | None,
    silver_refs: list[SilverWriteResult] | None = None,
    operation_errors: tuple[type[BaseException], ...],
) -> LayerWriteOutcome:
    """Write one layer; Gold requires COMPLETE, Silver may return no result.

    Schema violations are quarantined. Operational/quarantine failures propagate;
    incomplete Gold outcomes retain their receipt and never confirm record counts.
    """
    if layer not in {"silver", "gold"}:
        raise ValueError(
            f"safe_write_layer supports only 'silver' or 'gold' layers, got {layer!r}"
        )
    event_context = BatchWriteEventContext(
        emitter=context.domain_event_emitter,
        run_id=context.run_id,
        batch_id=batch_id,
        layer=layer,
        occurred_at=ingestion_ts,
        logger=context.logger,
    )
    try:
        write_result = await _execute_layer_write(
            execute_with_span=context.execute_with_span,
            writer=context.writer,
            layer=layer,
            records=records,
            batch_id=batch_id,
            ingestion_ts=ingestion_ts,
            bronze_refs=bronze_refs,
            silver_refs=silver_refs,
        )
        if layer == "gold":
            write_result = require_complete_gold_receipt(write_result)
        quarantined = (
            consume_gold_outcome_quarantine_count(context.writer)
            if layer == "gold"
            else 0
        )
        confirmed = max(len(records) - quarantined, 0)
        if confirmed == 0 and quarantined:
            return LayerWriteOutcome(
                layer=layer,
                status="quarantined",
                candidate_count=len(records),
                quarantined_count=quarantined,
                write_result=write_result,
            )
        context.writer.track_batch_written(stage=layer, count=confirmed)
        event_context.emit_written(confirmed)
        return LayerWriteOutcome(
            layer=layer,
            status="written",
            candidate_count=len(records),
            confirmed_count=confirmed,
            quarantined_count=quarantined,
            write_result=write_result,
        )
    except SchemaViolationError as error:
        await quarantine_schema_violation(
            writer=context.writer,
            quarantine_manager=context.quarantine_manager,
            event_context=event_context,
            records=records,
            error=error,
        )
        return LayerWriteOutcome(
            layer=layer,
            status="quarantined",
            candidate_count=len(records),
            quarantined_count=len(records),
        )
    except GoldWriteFailure as error:
        event_context.emit_failed(error)
        raise
    except operation_errors as error:
        if isinstance(error, Exception):
            event_context.emit_failed(error)
        raise


async def safe_write_silver(
    context: LayerWriteContext,
    records: list[dict[str, object]],
    batch_id: BatchID,
    ingestion_ts: datetime,
    bronze_refs: list[BronzeWriteResult] | None,
    operation_errors: tuple[type[BaseException], ...],
) -> LayerWriteOutcome:
    """Write Silver through the shared quarantine-aware layer path."""
    return await safe_write_layer(
        context=context,
        layer="silver",
        records=records,
        batch_id=batch_id,
        ingestion_ts=ingestion_ts,
        bronze_refs=bronze_refs,
        operation_errors=operation_errors,
    )


async def safe_write_gold(
    context: LayerWriteContext,
    records: list[dict[str, object]],
    batch_id: BatchID,
    ingestion_ts: datetime,
    silver_refs: list[SilverWriteResult] | None,
    operation_errors: tuple[type[BaseException], ...],
) -> LayerWriteOutcome:
    """Write Gold through the shared quarantine-aware layer path."""
    return await safe_write_layer(
        context=context,
        layer="gold",
        records=records,
        batch_id=batch_id,
        ingestion_ts=ingestion_ts,
        bronze_refs=None,
        silver_refs=silver_refs,
        operation_errors=operation_errors,
    )
