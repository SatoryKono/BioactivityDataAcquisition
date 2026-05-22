"""Orchestrates batch processing through Bronze, Silver, and Gold layers.

Observability: Nested spans for transform → write_bronze → write_silver → write_gold.

Safety Guard (RULES.md §4.6):
    Lock validation is performed at BatchWriter level BEFORE any write operation.
    RecordProcessor passes a lock_validator callback from LockRuntimeService.validate().
"""

from __future__ import annotations

from bioetl.domain.types import JsonDict

__all__ = ["RecordProcessor"]


from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import TYPE_CHECKING, cast

from bioetl.application.core.batch_executor import BatchResult
from bioetl.application.core.batch_runtime_failure_policy import OPERATION_ERRORS
from bioetl.application.core.span_helpers import close_span

if TYPE_CHECKING:
    from opentelemetry.trace import Span

    from bioetl.application.core.batch_metrics import BatchMetricsRecorderService
    from bioetl.application.core.batch_transformer import (
        BatchTransformer,
        TransformResult,
    )
    from bioetl.application.core.batch_writer import BatchWriter
    from bioetl.application.core.config import RecordProcessorConfig
    from bioetl.application.core.span_helpers import _ClosableSpan
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.ports import TracingPort
    from bioetl.domain.types import BatchID
    from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
    from bioetl.domain.value_objects.silver_result import SilverWriteResult


_PROCESSING_SPAN_ERRORS = OPERATION_ERRORS


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
    ) -> None:
        """Initialize RecordProcessor.

        Args:
            context: Pipeline execution context.
            batch_metrics: Metrics recorder for Bronze/Silver/Gold stages.
            transformer: Batch transformer for Bronze -> Silver/Gold conversion.
            writer: Batch writer orchestrating Bronze/Silver/Gold writes.
            config: Record processor configuration.
            tracer: Tracing port for distributed tracing.
        """
        _ = config
        self._context = context
        self._tracer = tracer
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
        bronze_result = await self._execute_with_span(
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
        result = await self._execute_transform_with_span(records, batch_id, start_index)
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
        silver_result = await self._execute_with_span(
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
        await self._execute_with_span(
            "write_gold",
            self._writer.write_gold(result.gold_records, silver_refs=silver_refs),
            batch_id,
            len(result.gold_records),
            on_error=lambda e: self._writer.log_and_track_write_error(
                "gold", e, batch_id
            ),
        )

    async def _execute_with_span(
        self,
        name: str,
        coro: Awaitable[object],  # Awaitable: coroutine type varies per pipeline stage
        batch_id: BatchID,
        count: int,
        on_error: Callable[[Exception], object]
        | None = None,  # callback for error handling
    ) -> object:  # object: callback return type varies
        """Execute coroutine with tracing span."""
        span = self._start_span(name, batch_id, count)
        try:
            result = await coro
            self._end_span(span)
            return result
        except _PROCESSING_SPAN_ERRORS as e:
            self._end_span(span, e)
            if on_error:
                on_error(e)
            raise

    async def _execute_transform_with_span(
        # Any: record vals vary
        self,
        records: list[JsonDict],  # Any: values are heterogeneous
        batch_id: BatchID,
        start_index: int,
    ) -> TransformResult:
        """Execute transformation with extended span attributes."""
        span = self._start_span("transform", batch_id, len(records), input_count=True)
        try:
            result = await self._transformer.transform_batch(
                records, batch_id, start_index=start_index
            )
            if span:
                span.set_attribute("bioetl.silver_count", len(result.silver_records))
                span.set_attribute("bioetl.gold_count", len(result.gold_records))
                span.set_attribute("bioetl.quarantined_count", result.quarantined_count)
            self._end_span(span)
            return result
        except _PROCESSING_SPAN_ERRORS as e:
            self._end_span(span, e)
            raise

    def _start_span(
        self, name: str, batch_id: BatchID, count: int, input_count: bool = False
    ) -> Span | None:  # OTel Span or None if tracer unavailable
        """Start a tracing span if tracer is available."""
        if not self._tracer:
            return None
        count_key = "bioetl.input_count" if input_count else "bioetl.record_count"
        attrs = {"bioetl.batch_id": str(batch_id), count_key: count}
        span = self._tracer.get_tracer("bioetl.processor").start_as_current_span(
            name, attributes=attrs
        )
        typed_span = cast("Span", span)
        typed_span.__enter__()
        return typed_span

    def _end_span(self, span: Span | None, error: Exception | None = None) -> None:
        """End a tracing span."""
        close_span(cast("_ClosableSpan | None", span), error)
