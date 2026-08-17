"""Silver/Gold write choreography helpers for batch processing support."""

from __future__ import annotations

from collections.abc import Awaitable
from datetime import datetime
from typing import TYPE_CHECKING, Protocol, cast

from bioetl.application.core._batch_processing_metrics_support import (
    track_storage_write_metrics,
)
from bioetl.application.core._batch_write_support import safe_write_layer
from bioetl.application.core.batch_shared_operation_errors import (
    OPERATION_ERRORS as _OPERATION_ERRORS,
)
from bioetl.application.core.batch_transformer import TransformResult
from bioetl.domain.types import BatchID, RunID
from bioetl.domain.value_objects.silver_result import SilverWriteResult

if TYPE_CHECKING:
    from bioetl.application.core.batch_metrics import BatchMetricsRecorderService
    from bioetl.application.core.batch_writer import BatchWriter
    from bioetl.application.core.quarantine_manager import QuarantineRuntimeService
    from bioetl.application.observability.domain_event_emitter import (
        DomainEventEmitterProtocol,
    )
    from bioetl.domain.ports import LoggerPort
    from bioetl.domain.value_objects.bronze_result import BronzeWriteResult

__all__ = ["LayerSpanRunner", "write_silver_then_gold"]


class LayerSpanRunner(Protocol):
    """Span runner used to execute one layer write under tracing."""

    def __call__(
        self,
        *args: object,
        **kwargs: object,
    ) -> Awaitable[object]: ...


async def write_silver_then_gold(
    *,
    execute_with_span: LayerSpanRunner,
    writer: BatchWriter,
    quarantine_manager: QuarantineRuntimeService,
    logger: LoggerPort,
    batch_metrics: BatchMetricsRecorderService,
    run_id: RunID | None,
    domain_event_emitter: DomainEventEmitterProtocol | None,
    transform_result: TransformResult,
    batch_id: BatchID,
    ingestion_ts: datetime,
    bronze_refs: list[BronzeWriteResult] | None,
) -> None:
    """Write Silver first, then pass lineage refs into Gold."""
    silver_result: SilverWriteResult | None = None
    silver_written = 0
    gold_written = 0
    if transform_result.silver_records:
        silver_outcome = await safe_write_layer(
            execute_with_span=execute_with_span,
            writer=writer,
            quarantine_manager=quarantine_manager,
            logger=logger,
            run_id=run_id,
            domain_event_emitter=domain_event_emitter,
            layer="silver",
            records=transform_result.silver_records,
            batch_id=batch_id,
            ingestion_ts=ingestion_ts,
            bronze_refs=bronze_refs,
            operation_errors=_OPERATION_ERRORS,
        )
        if silver_outcome is None:
            track_storage_write_metrics(
                batch_metrics,
                transform_result=transform_result,
                silver_written=0,
                gold_written=0,
            )
            return
        if silver_outcome is not True:
            silver_result = cast("SilverWriteResult", silver_outcome)
        silver_written = len(transform_result.silver_records)
    if transform_result.gold_records:
        gold_outcome = await safe_write_layer(
            execute_with_span=execute_with_span,
            writer=writer,
            quarantine_manager=quarantine_manager,
            logger=logger,
            run_id=run_id,
            domain_event_emitter=domain_event_emitter,
            layer="gold",
            records=transform_result.gold_records,
            batch_id=batch_id,
            ingestion_ts=ingestion_ts,
            bronze_refs=None,
            silver_refs=[silver_result] if silver_result is not None else None,
            operation_errors=_OPERATION_ERRORS,
        )
        if gold_outcome is not None:
            gold_written = len(transform_result.gold_records)
    track_storage_write_metrics(
        batch_metrics,
        transform_result=transform_result,
        silver_written=silver_written,
        gold_written=gold_written,
    )
