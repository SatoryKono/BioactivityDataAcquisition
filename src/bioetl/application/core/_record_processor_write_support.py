"""Silver/Gold layer-write helpers for the RecordProcessor compat path.

Quarantine-configured runs delegate to ``safe_write_layer`` for parity with
``BatchProcessingService``; without a quarantine manager the legacy direct
writer calls are kept unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from bioetl.application.core._batch_processing_layer_write_support import (
    OPERATION_ERRORS,
)
from bioetl.application.core._batch_write_support import (
    SafeLayerWriteContext,
    build_layer_write_outcome,
)

if TYPE_CHECKING:
    from datetime import datetime

    from bioetl.application.core._record_processor_span_support import (
        RecordProcessorSpanExecutor,
    )
    from bioetl.application.core.batch_processing_contracts import LayerWriteOutcome
    from bioetl.application.core.batch_transformer import TransformResult
    from bioetl.application.core.batch_writer import BatchWriter
    from bioetl.application.core.quarantine_manager import QuarantineRuntimeService
    from bioetl.application.observability.domain_event_emitter import (
        DomainEventEmitterProtocol,
    )
    from bioetl.domain.ports import LoggerPort
    from bioetl.domain.types import BatchID, RunID
    from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
    from bioetl.domain.value_objects.silver_result import SilverWriteResult


@dataclass(frozen=True)
class RecordProcessorWriteDependencies:
    """Optional collaborators for write-stage parity with the canonical path."""

    quarantine_manager: QuarantineRuntimeService | None = None
    domain_event_emitter: DomainEventEmitterProtocol | None = None
    operation_errors: tuple[type[BaseException], ...] = OPERATION_ERRORS


async def write_silver_layer(
    *,
    span_executor: RecordProcessorSpanExecutor,
    writer: BatchWriter,
    quarantine_manager: QuarantineRuntimeService | None,
    logger: LoggerPort,
    run_id: RunID | None,
    domain_event_emitter: DomainEventEmitterProtocol | None,
    result: TransformResult,
    batch_id: BatchID,
    ingestion_ts: datetime,
    bronze_refs: list[BronzeWriteResult] | None,
    operation_errors: tuple[type[BaseException], ...],
) -> LayerWriteOutcome:
    """Write Silver with quarantine parity when a manager is configured."""
    if not result.silver_records:
        return build_layer_write_outcome(
            layer="silver",
            status="skipped",
            candidate_count=0,
        )
    if quarantine_manager is None:
        silver_result = await span_executor.execute_with_span(
            "write_silver",
            writer.write_silver(
                result.silver_records,
                batch_id,
                ingestion_ts,
                bronze_refs=bronze_refs,
            ),
            batch_id,
            len(result.silver_records),
            on_error=lambda e: writer.log_and_track_write_error("silver", e, batch_id),
        )
        return build_layer_write_outcome(
            layer="silver",
            status="written",
            candidate_count=len(result.silver_records),
            confirmed_count=len(result.silver_records),
            write_result=cast("SilverWriteResult | None", silver_result),
        )
    safe_writer = SafeLayerWriteContext(
        execute_with_span=span_executor.execute_with_span,
        writer=writer,
        quarantine_manager=quarantine_manager,
        logger=logger,
        run_id=run_id,
        domain_event_emitter=domain_event_emitter,
        batch_id=batch_id,
        ingestion_ts=ingestion_ts,
        operation_errors=operation_errors,
    )
    return await safe_writer.write(
        layer="silver",
        records=result.silver_records,
        bronze_refs=bronze_refs,
    )


async def write_gold_layer(
    *,
    span_executor: RecordProcessorSpanExecutor,
    writer: BatchWriter,
    quarantine_manager: QuarantineRuntimeService | None,
    logger: LoggerPort,
    run_id: RunID | None,
    domain_event_emitter: DomainEventEmitterProtocol | None,
    result: TransformResult,
    batch_id: BatchID,
    ingestion_ts: datetime,
    silver_outcome: LayerWriteOutcome,
    operation_errors: tuple[type[BaseException], ...],
) -> LayerWriteOutcome:
    """Write Gold after Silver; blocked when Silver was quarantined."""
    if not result.gold_records:
        return build_layer_write_outcome(
            layer="gold",
            status="skipped",
            candidate_count=0,
        )
    if silver_outcome.status == "quarantined":
        return build_layer_write_outcome(
            layer="gold",
            status="blocked",
            candidate_count=len(result.gold_records),
        )
    silver_result = cast("SilverWriteResult | None", silver_outcome.write_result)
    silver_refs = [silver_result] if silver_result is not None else None
    if quarantine_manager is None:
        await span_executor.execute_with_span(
            "write_gold",
            writer.write_gold(result.gold_records, silver_refs=silver_refs),
            batch_id,
            len(result.gold_records),
            on_error=lambda e: writer.log_and_track_write_error("gold", e, batch_id),
        )
        return build_layer_write_outcome(
            layer="gold",
            status="written",
            candidate_count=len(result.gold_records),
            confirmed_count=len(result.gold_records),
        )
    safe_writer = SafeLayerWriteContext(
        execute_with_span=span_executor.execute_with_span,
        writer=writer,
        quarantine_manager=quarantine_manager,
        logger=logger,
        run_id=run_id,
        domain_event_emitter=domain_event_emitter,
        batch_id=batch_id,
        ingestion_ts=ingestion_ts,
        operation_errors=operation_errors,
    )
    return await safe_writer.write(
        layer="gold",
        records=result.gold_records,
        bronze_refs=None,
        silver_refs=silver_refs,
    )
