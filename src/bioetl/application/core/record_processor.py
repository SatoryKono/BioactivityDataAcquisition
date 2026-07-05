"""Orchestrates batch processing through Bronze, Silver, and Gold layers.

Observability: Nested spans for transform → write_bronze → write_silver → write_gold.

Safety Guard (RULES.md §4.6):
    Lock validation is performed at BatchWriter level BEFORE any write operation.
    RecordProcessor passes a lock_validator callback from LockRuntimeService.validate().
"""

from __future__ import annotations

from bioetl.domain.types import JsonDict

__all__ = ["RecordProcessor"]


from collections.abc import Callable
from datetime import datetime
from typing import TYPE_CHECKING, cast

from bioetl.application.core._record_processor_span_support import (
    RecordProcessorSpanExecutor,
)
from bioetl.application.core.batch_executor import BatchResult

if TYPE_CHECKING:
    from bioetl.application.core.batch_metrics import BatchMetricsRecorderService
    from bioetl.application.core.batch_transformer import (
        BatchTransformer,
        TransformResult,
    )
    from bioetl.application.core.batch_writer import BatchWriter
    from bioetl.application.core.record_processor_config import RecordProcessorConfig
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.ports import TracingPort
    from bioetl.domain.types import BatchID
    from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
    from bioetl.domain.value_objects.silver_result import SilverWriteResult


class RecordProcessor:
    """Orchestrates batch transformation and writing across all layers."""

    def __init__(
        self,
        context: PipelineContext,
        batch_metrics: BatchMetricsRecorderService,
        transformer: BatchTransformer,
        writer: BatchWriter,
        config: RecordProcessorConfig,
        tracer: TracingPort,
        span_executor_factory: Callable[
            [TracingPort], RecordProcessorSpanExecutor
        ] = RecordProcessorSpanExecutor,
    ) -> None:
        """Initialize RecordProcessor.

        Args:
            context: Pipeline execution context.
            batch_metrics: Metrics recorder for Bronze/Silver/Gold stages.
            transformer: Batch transformer for Bronze -> Silver/Gold conversion.
            writer: Batch writer orchestrating Bronze/Silver/Gold writes.
            config: Record processor configuration.
            tracer: Tracing port for distributed tracing.
            span_executor_factory: Factory for the tracing span executor.
        """
        _ = config
        self._context = context
        span_executor = span_executor_factory(tracer)
        self._span_executor = span_executor
        self._batch_metrics = batch_metrics
        self._transformer = transformer
        self._writer = writer

    async def process_batch(
        # Any: record vals vary
        self,
        records: list[JsonDict],  # Any: values are heterogeneous
        batch_id: BatchID,
        start_index: int = 0,
    ) -> BatchResult:
        """Process batch through Bronze -> Silver -> Gold with tracing.

        Args:
            records: Raw Bronze records fetched from the data source.
            batch_id: Unique identifier for this batch used in tracing and storage.
            start_index: Absolute record index of the first record for accurate reporting.

        Returns:
            BatchResult with bronze, silver, gold, and quarantined record counts.
        """
        ingestion_ts = self._context.started_at
        self._batch_metrics.track_records_fetched(len(records))
        bronze_result = await self._span_executor.execute_with_span(
            "write_bronze",
            self._writer.write_bronze(records, batch_id, ingestion_ts),
            batch_id,
            len(records),
            on_error=lambda e: self._writer.log_and_track_write_error(
                "bronze", e, batch_id
            ),
        )
        self._batch_metrics.track_batch_size("bronze", len(records))
        self._batch_metrics.track_processed_records("bronze", len(records))
        result = await self._span_executor.execute_transform_with_span(
            transformer=self._transformer,
            records=records,
            batch_id=batch_id,
            start_index=start_index,
        )
        self._track_transform_metrics(result)
        bronze_refs = self._build_bronze_refs(bronze_result)
        silver_result = await self._write_silver_if_present(
            result=result,
            batch_id=batch_id,
            ingestion_ts=ingestion_ts,
            bronze_refs=bronze_refs,
        )
        await self._write_gold_if_present(
            result=result,
            batch_id=batch_id,
            silver_refs=[silver_result] if silver_result is not None else None,
        )

        return BatchResult(
            bronze_count=len(records),
            silver_count=len(result.silver_records),
            gold_count=len(result.gold_records),
            quarantined_count=result.quarantined_count,
        )

    def _track_transform_metrics(self, result: TransformResult) -> None:
        self._batch_metrics.track_processed_records(
            "quarantined", result.quarantined_count
        )
        self._batch_metrics.track_processed_records(
            "silver", len(result.silver_records)
        )
        self._batch_metrics.track_processed_records("gold", len(result.gold_records))

    def _build_bronze_refs(
        self, bronze_result: object
    ) -> list[BronzeWriteResult] | None:
        typed_bronze_result = cast("BronzeWriteResult | None", bronze_result)
        return [typed_bronze_result] if typed_bronze_result else None

    async def _write_silver_if_present(
        self,
        *,
        result: TransformResult,
        batch_id: BatchID,
        ingestion_ts: datetime,
        bronze_refs: list[BronzeWriteResult] | None,
    ) -> SilverWriteResult | None:
        if not result.silver_records:
            return None
        silver_result = await self._span_executor.execute_with_span(
            "write_silver",
            self._writer.write_silver(
                result.silver_records,
                batch_id,
                ingestion_ts,
                bronze_refs=bronze_refs,
            ),
            batch_id,
            len(result.silver_records),
            on_error=lambda e: self._writer.log_and_track_write_error(
                "silver", e, batch_id
            ),
        )
        return cast("SilverWriteResult | None", silver_result)

    async def _write_gold_if_present(
        self,
        *,
        result: TransformResult,
        batch_id: BatchID,
        silver_refs: list[SilverWriteResult] | None = None,
    ) -> None:
        if not result.gold_records:
            return
        await self._span_executor.execute_with_span(
            "write_gold",
            self._writer.write_gold(result.gold_records, silver_refs=silver_refs),
            batch_id,
            len(result.gold_records),
            on_error=lambda e: self._writer.log_and_track_write_error(
                "gold", e, batch_id
            ),
        )
