"""Support service for BatchProcessingService execution choreography."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import TYPE_CHECKING, TypeVar

from bioetl.application.core._batch_write_support import (
    emit_batch_written,
    emit_domain_event,
    safe_write_layer,
)
from bioetl.application.core.batch_processing_runtime import (
    build_bronze_refs,
    execute_transform_with_span,
    execute_with_layer_span,
    execute_with_pipeline_failure_policy,
    get_source_metadata,
)
from bioetl.application.core.batch_runtime_failure_policy import (
    OPERATION_ERRORS as _RF005_OPERATION_ERRORS,
)
from bioetl.application.core.batch_runtime_failure_policy import (
    PIPELINE_EXECUTION_ERRORS as _RF005_SHARED_FAILURE_POLICY,
)
from bioetl.application.core.batch_transformer import TransformResult
from bioetl.application.core.quarantine_manager import QuarantineManagerService
from bioetl.domain.aggregates.events import DomainEvent
from bioetl.domain.models.metadata import SourceMetadata
from bioetl.domain.types import BatchID, BronzeRecord, RunID

__all__ = ["BatchProcessingSupportService"]

if TYPE_CHECKING:
    from opentelemetry.trace import Span

    from bioetl.application.core.batch_metrics import BatchMetricsRecorderService
    from bioetl.application.core.batch_tracing import BatchTracingManagerService
    from bioetl.application.core.batch_transformer import BatchTransformer
    from bioetl.application.core.batch_writer import BatchWriter
    from bioetl.application.core.pipeline_services import PipelineService
    from bioetl.application.observability.domain_event_emitter import (
        DomainEventEmitterPort,
    )
    from bioetl.domain.ports import LoggerPort
    from bioetl.domain.value_objects.bronze_result import BronzeWriteResult

_ResultT = TypeVar("_ResultT")
_SHARED_FAILURE_POLICY = _RF005_SHARED_FAILURE_POLICY
_OPERATION_ERRORS = _RF005_OPERATION_ERRORS


class BatchProcessingSupportService:
    """Encapsulate per-batch transform/write tracing choreography."""

    def __init__(
        self,
        *,
        services: PipelineService,
        logger: LoggerPort,
        batch_metrics: BatchMetricsRecorderService,
        transformer: BatchTransformer,
        writer: BatchWriter,
        tracing: BatchTracingManagerService,
        quarantine_manager: QuarantineManagerService,
        run_id: RunID | None = None,
        domain_event_emitter: DomainEventEmitterPort | None = None,
    ) -> None:
        self._services = services
        self._logger = logger
        self._batch_metrics = batch_metrics
        self._transformer = transformer
        self._writer = writer
        self._tracing = tracing
        self._quarantine_manager = quarantine_manager
        self._run_id = run_id
        self._domain_event_emitter = domain_event_emitter

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
                "bronze", error, batch_id
            ),
        )
        self._batch_metrics.track_batch_size("bronze", len(records))
        self._batch_metrics.track_processed_records("bronze", len(records))
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
        self._batch_metrics.track_processed_records(
            "silver", len(transform_result.silver_records)
        )
        self._batch_metrics.track_processed_records(
            "gold", len(transform_result.gold_records)
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
        write_coros: list[Awaitable[object]] = []
        if transform_result.silver_records:
            write_coros.append(
                safe_write_layer(
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
                )
            )
        if transform_result.gold_records:
            write_coros.append(
                safe_write_layer(
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
                    operation_errors=_OPERATION_ERRORS,
                )
            )
        if write_coros:
            await asyncio.gather(*write_coros)

    def finalize_batch_span(
        self,
        *,
        span: Span | None,
        records: list[BronzeRecord],
        transform_result: TransformResult,
    ) -> None:
        self._tracing.set_batch_result(
            span,
            bronze_count=len(records),
            silver_count=len(transform_result.silver_records),
            gold_count=len(transform_result.gold_records),
            quarantined_count=transform_result.quarantined_count,
        )
        self._tracing.end_span(span)

    async def execute_with_pipeline_failure_policy(
        self,
        *,
        span: Span | None,
        work_coro: Awaitable[_ResultT],
    ) -> _ResultT:
        return await execute_with_pipeline_failure_policy(
            tracing=self._tracing,
            span=span,
            work_coro=work_coro,
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
        self,
        *,
        records: list[BronzeRecord],
        batch_id: BatchID,
        start_index: int,
    ) -> TransformResult:
        return await execute_transform_with_span(
            tracing=self._tracing,
            transformer=self._transformer,
            records=records,
            batch_id=batch_id,
            start_index=start_index,
        )

    @staticmethod
    def build_bronze_refs(bronze_result: object) -> list[BronzeWriteResult] | None:
        return build_bronze_refs(bronze_result)

    def emit_domain_event(self, event: DomainEvent) -> None:
        emit_domain_event(self._domain_event_emitter, event)
