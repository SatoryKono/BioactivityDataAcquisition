"""Support service for BatchProcessingService execution choreography."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import TYPE_CHECKING, TypeVar, cast

from bioetl.application.core._batch_processing_metrics_support import (
    track_bronze_write_metrics,
    track_storage_write_metrics,
    track_transform_result_metrics,
)
from bioetl.application.core._batch_write_support import (
    emit_batch_written,
    emit_domain_event,
    safe_write_layer,
)
from bioetl.application.core.batch_processing_runtime import (
    execute_transform_with_span,
    execute_with_layer_span,
    get_source_metadata,
)
from bioetl.application.core.batch_runtime_failure_policy import (
    OPERATION_ERRORS as SHARED_OPERATION_ERRORS,
)
from bioetl.application.core.batch_runtime_failure_policy import (
    PIPELINE_EXECUTION_ERRORS as _RF005_SHARED_FAILURE_POLICY,
)
from bioetl.application.core.batch_transformer import TransformResult
from bioetl.domain.aggregates.events import DomainEvent
from bioetl.domain.models.metadata import SourceMetadata
from bioetl.domain.types import BatchID, BronzeRecord, RunID
from bioetl.domain.value_objects.silver_result import SilverWriteResult

__all__ = ["BatchProcessingSupportService"]

if TYPE_CHECKING:
    from bioetl.application.core.batch_metrics import BatchMetricsRecorderService
    from bioetl.application.core.batch_tracing import BatchTracingManagerService
    from bioetl.application.core.batch_transformer import BatchTransformer
    from bioetl.application.core.batch_writer import BatchWriter
    from bioetl.application.core.pipeline_service_protocols import (
        PipelineDataSourceServicesProtocol,
    )
    from bioetl.application.core.quarantine_manager import QuarantineRuntimeService
    from bioetl.application.observability.domain_event_emitter import (
        DomainEventEmitterProtocol,
    )
    from bioetl.application.services.debug_export_service import DebugExportService
    from bioetl.domain.ports import LoggerPort
    from bioetl.domain.value_objects.bronze_result import BronzeWriteResult

_ResultT = TypeVar("_ResultT")
_SHARED_FAILURE_POLICY = _RF005_SHARED_FAILURE_POLICY
_OPERATION_ERRORS = SHARED_OPERATION_ERRORS


class BatchProcessingSupportService:
    """Encapsulate per-batch transform/write tracing choreography."""

    def __init__(
        self,
        *,
        services: PipelineDataSourceServicesProtocol,
        logger: LoggerPort,
        batch_runtime: dict[str, object] | None = None,
        run_id: RunID | None = None,
        domain_event_emitter: DomainEventEmitterProtocol | None = None,
        debug_export_service: DebugExportService | None = None,
        **legacy: object,
    ) -> None:
        """Initialize batch processing support.

        Prefer ``batch_runtime`` dict. Transitional/unit callers may pass
        individual collaborators via keyword args.
        """
        resolved_runtime = dict(batch_runtime or {})
        for key in (
            "batch_metrics",
            "transformer",
            "writer",
            "tracing",
            "quarantine_manager",
        ):
            if key in legacy and legacy[key] is not None:
                resolved_runtime[key] = legacy.pop(key)
        if legacy:
            raise TypeError(
                "BatchProcessingSupportService() got unexpected keyword argument(s): "
                + ", ".join(sorted(str(k) for k in legacy))
            )
        self._services = services
        self._logger = logger
        self._batch_metrics = cast(
            "BatchMetricsRecorderService", resolved_runtime["batch_metrics"]
        )
        self._transformer = cast("BatchTransformer", resolved_runtime["transformer"])
        self._writer = cast("BatchWriter", resolved_runtime["writer"])
        self._tracing = cast("BatchTracingManagerService", resolved_runtime["tracing"])
        self._quarantine_manager = cast(
            "QuarantineRuntimeService", resolved_runtime["quarantine_manager"]
        )
        self._run_id = run_id
        self._domain_event_emitter = domain_event_emitter
        self._debug_export_service = debug_export_service

    def get_source_metadata(self, query_string: str | None) -> SourceMetadata | None:
        return get_source_metadata(
            data_source=self._services.data_source,
            logger=self._logger,
            query_string=query_string,
        )

    async def write_bronze_layer(
        self,
        *,
        records: list[BronzeRecord],
        batch_id: BatchID,
        start_index: int,
        ingestion_ts: datetime,
        source_metadata: SourceMetadata | None,
    ) -> object:
        result = await self._execute_with_span(
            "write_bronze",
            self._writer.write_bronze(
                records,
                batch_id,
                ingestion_ts,
                source_metadata=source_metadata,
            ),
            batch_id,
            len(records),
            on_error=lambda error: self._writer.log_and_track_write_error(
                "bronze", error, batch_id, record_count=len(records)
            ),
        )
        track_bronze_write_metrics(
            self._batch_metrics,
            record_count=len(records),
        )
        if self._debug_export_service is not None:
            self._debug_export_service.record_bronze_batch(
                records=records,
                batch_id=batch_id,
                start_index=start_index,
                source_metadata=source_metadata,
            )
        emit_batch_written(
            emitter=self._domain_event_emitter,
            run_id=self._run_id,
            batch_id=batch_id,
            layer="bronze",
            record_count=len(records),
            occurred_at=ingestion_ts,
        )
        return result

    async def transform_and_track_metrics(
        self,
        *,
        records: list[BronzeRecord],
        batch_id: BatchID,
        start_index: int,
    ) -> TransformResult:
        transform_result = await self._execute_transform_with_span(
            records=records,
            batch_id=batch_id,
            start_index=start_index,
        )
        track_transform_result_metrics(
            self._batch_metrics,
            transform_result=transform_result,
        )
        return transform_result

    async def write_silver_gold_concurrent(
        self,
        *,
        transform_result: TransformResult,
        batch_id: BatchID,
        ingestion_ts: datetime,
        bronze_refs: list[BronzeWriteResult] | None,
    ) -> None:
        """Write Silver first, then pass its lineage refs into Gold.

        The historical method name is preserved for caller compatibility.
        """
        silver_result: SilverWriteResult | None = None
        if transform_result.silver_records:
            silver_result = cast(
                "SilverWriteResult | None",
                await safe_write_layer(
                    execute_with_span=self._execute_with_span,
                    writer=self._writer,
                    quarantine_manager=self._quarantine_manager,
                    logger=self._logger,
                    run_id=self._run_id,
                    domain_event_emitter=self._domain_event_emitter,
                    layer="silver",
                    records=transform_result.silver_records,
                    batch_id=batch_id,
                    ingestion_ts=ingestion_ts,
                    bronze_refs=bronze_refs,
                    operation_errors=_OPERATION_ERRORS,
                ),
            )
        if transform_result.gold_records:
            await safe_write_layer(
                execute_with_span=self._execute_with_span,
                writer=self._writer,
                quarantine_manager=self._quarantine_manager,
                logger=self._logger,
                run_id=self._run_id,
                domain_event_emitter=self._domain_event_emitter,
                layer="gold",
                records=transform_result.gold_records,
                batch_id=batch_id,
                ingestion_ts=ingestion_ts,
                bronze_refs=None,
                silver_refs=[silver_result] if silver_result is not None else None,
                operation_errors=_OPERATION_ERRORS,
            )
        track_storage_write_metrics(
            self._batch_metrics,
            transform_result=transform_result,
        )

    async def _execute_with_span(
        self,
        name: str,
        coro: Awaitable[object],
        batch_id: BatchID,
        count: int,
        on_error: Callable[[Exception], None] | None = None,
    ) -> object:
        return await execute_with_layer_span(
            tracing=self._tracing,
            name=name,
            coro=coro,
            batch_id=batch_id,
            count=count,
            on_error=on_error,
        )

    async def _execute_transform_with_span(
        self, *, records: list[BronzeRecord], batch_id: BatchID, start_index: int
    ) -> TransformResult:
        return await execute_transform_with_span(
            tracing=self._tracing,
            transformer=self._transformer,
            records=records,
            batch_id=batch_id,
            start_index=start_index,
        )

    def emit_domain_event(self, event: DomainEvent) -> None:
        emit_domain_event(self._domain_event_emitter, event)
