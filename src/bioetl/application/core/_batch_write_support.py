"""Private write-path helpers for ``BatchProcessingSupportService``."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from bioetl.application.core._batch_write_events import (
    BatchFailureEventContext,
    emit_batch_failed,
    emit_batch_written,
    emit_domain_event,
)
from bioetl.application.core._batch_write_schema_quarantine import (
    quarantine_schema_violation,
)
from bioetl.application.core.batch_processing_contracts import (
    LayerWriteOutcome,
    WriteLayerStatus,
)
from bioetl.application.core.quarantine_manager import (
    QuarantineRuntimeService,
)
from bioetl.domain.exceptions import SchemaViolationError
from bioetl.domain.types import BatchID, RunID

if TYPE_CHECKING:
    from bioetl.application.core.batch_writer import BatchWriter
    from bioetl.application.observability.domain_event_emitter import (
        DomainEventEmitterProtocol,
    )
    from bioetl.domain.ports import LoggerPort
    from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
    from bioetl.domain.value_objects.silver_result import SilverWriteResult

__all__ = [
    "SafeLayerWriteContext",
    "build_layer_write_outcome",
    "emit_batch_failed",
    "emit_batch_written",
    "emit_domain_event",
    "safe_write_layer",
]


@dataclass(frozen=True, slots=True)
class SafeLayerWriteContext:
    """Collaborators shared by Silver and Gold safe-write invocations."""

    execute_with_span: Callable[..., Awaitable[object]]
    writer: BatchWriter
    quarantine_manager: QuarantineRuntimeService
    logger: LoggerPort
    run_id: RunID | None
    domain_event_emitter: DomainEventEmitterProtocol | None
    batch_id: BatchID
    ingestion_ts: datetime
    operation_errors: tuple[type[BaseException], ...]

    async def write(
        self,
        *,
        layer: str,
        records: list[dict[str, object]],
        bronze_refs: list[BronzeWriteResult] | None,
        silver_refs: list[SilverWriteResult] | None = None,
    ) -> LayerWriteOutcome:
        """Write one layer through the canonical guarded implementation."""
        return await safe_write_layer(
            execute_with_span=self.execute_with_span,
            writer=self.writer,
            quarantine_manager=self.quarantine_manager,
            logger=self.logger,
            run_id=self.run_id,
            domain_event_emitter=self.domain_event_emitter,
            layer=layer,
            records=records,
            batch_id=self.batch_id,
            ingestion_ts=self.ingestion_ts,
            bronze_refs=bronze_refs,
            silver_refs=silver_refs,
            operation_errors=self.operation_errors,
        )


def build_layer_write_outcome(
    *,
    layer: str,
    status: WriteLayerStatus,
    candidate_count: int,
    confirmed_count: int = 0,
    quarantined_count: int = 0,
    write_result: object | None = None,
) -> LayerWriteOutcome:
    """Build the shared immutable result for one Silver or Gold write."""
    return LayerWriteOutcome(
        layer=layer,
        status=status,
        candidate_count=candidate_count,
        confirmed_count=confirmed_count,
        quarantined_count=quarantined_count,
        write_result=write_result,
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
    if layer == "silver":
        operation = writer.write_silver(
            records,
            batch_id,
            ingestion_ts,
            bronze_refs=bronze_refs,
        )
    else:
        operation = writer.write_gold(records, silver_refs=silver_refs)

    def _track_write_error(error: Exception) -> None:
        writer.log_and_track_write_error(
            layer,
            error,
            batch_id,
            record_count=len(records),
        )

    return await execute_with_span(
        f"write_{layer}",
        operation,
        batch_id,
        len(records),
        on_error=_track_write_error,
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
) -> LayerWriteOutcome:
    """Execute one layer write and quarantine schema-invalid outputs.

    Returns a typed outcome: ``written`` when the writer port call completed
    (even when the port itself returns ``None``, as Gold does), or
    ``quarantined`` after the records were persisted to quarantine. Operational
    errors and quarantine-write failures propagate to the caller.
    """
    if layer not in {"silver", "gold"}:
        raise ValueError(
            f"safe_write_layer supports only 'silver' or 'gold' layers, got {layer!r}"
        )
    failure_context = BatchFailureEventContext(
        domain_event_emitter,
        run_id,
        batch_id,
        layer,
        ingestion_ts,
        logger,
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
        return build_layer_write_outcome(
            layer=layer,
            status="written",
            candidate_count=len(records),
            confirmed_count=len(records),
            write_result=write_result,
        )
    except SchemaViolationError as error:
        await quarantine_schema_violation(
            writer=writer,
            quarantine_manager=quarantine_manager,
            logger=logger,
            failure_context=failure_context,
            records=records,
            error=error,
        )
        return build_layer_write_outcome(
            layer=layer,
            status="quarantined",
            candidate_count=len(records),
            quarantined_count=len(records),
        )
    except operation_errors as error:
        if isinstance(error, Exception):
            failure_context.emit(error)
        raise
