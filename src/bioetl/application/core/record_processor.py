"""Orchestrates batch processing through Bronze, Silver, and Gold layers.

Observability: Nested spans for transform → write_bronze → write_silver → write_gold.

Safety Guard (RULES.md §4.6):
    Lock validation is performed at BatchWriter level BEFORE any write operation.
    RecordProcessor passes a lock_validator callback from LockManager.validate().
"""

from __future__ import annotations

__all__ = ["RecordProcessor"]


from typing import TYPE_CHECKING, Any

from bioetl.application.core.batch_executor import BatchResult
from bioetl.domain.exceptions import BioETLError

if TYPE_CHECKING:
    from opentelemetry.trace import Span

    from bioetl.application.core.batch_metrics import BatchMetricsRecorderService
    from bioetl.application.core.batch_transformer import (
        BatchTransformer,
        TransformResult,
    )
    from bioetl.application.core.batch_writer import BatchWriter
    from bioetl.application.core.config import RecordProcessorConfig
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.ports import TracingPort
    from bioetl.domain.types import BatchID


_PROCESSING_SPAN_ERRORS = (
    BioETLError,
    OSError,
    RuntimeError,
    ValueError,
    TypeError,
)


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
        records: list[dict[str, Any]],  # Any: values are heterogeneous
        batch_id: BatchID,
        start_index: int = 0,
    ) -> BatchResult:
        """Process batch through Bronze -> Silver -> Gold with tracing.

        Args:
            records: Collection of data records.
            batch_id: Batch identifier.
            start_index: Start index.

        Returns:
            Processed result.
        """
        ingestion_ts = self._context.started_at

        # Write to Bronze and capture result for lineage tracking (REQ-LINEAGE-001)
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

        # Transform records
        result = await self._execute_transform_with_span(records, batch_id, start_index)
        self._batch_metrics.track_processed_records(
            "quarantined", result.quarantined_count
        )
        self._batch_metrics.track_processed_records(
            "silver", len(result.silver_records)
        )
        self._batch_metrics.track_processed_records("gold", len(result.gold_records))

        # Write to Silver with bronze_refs for lineage tracking (REQ-LINEAGE-001)
        bronze_refs = [bronze_result] if bronze_result else None
        if result.silver_records:
            await self._execute_with_span(
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

        # Write to Gold
        if result.gold_records:
            await self._execute_with_span(
                "write_gold",
                self._writer.write_gold(result.gold_records),
                batch_id,
                len(result.gold_records),
                on_error=lambda e: self._writer.log_and_track_write_error(
                    "gold", e, batch_id
                ),
            )

        return BatchResult(
            bronze_count=len(records),
            silver_count=len(result.silver_records),
            gold_count=len(result.gold_records),
            quarantined_count=result.quarantined_count,
        )

    async def _execute_with_span(
        self,
        name: str,
        coro: Any,  # Any: coroutine type varies per pipeline stage
        batch_id: BatchID,
        count: int,
        on_error: Any = None,  # Any: error callback type varies per caller
    ) -> Any:  # Any: callback return type varies
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
        records: list[dict[str, Any]],  # Any: values are heterogeneous
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
    ) -> Any:  # Any: OTel Span (avoids opentelemetry import)
        """Start a tracing span if tracer is available."""
        if not self._tracer:
            return None
        count_key = "bioetl.input_count" if input_count else "bioetl.record_count"
        attrs = {"bioetl.batch_id": str(batch_id), count_key: count}
        span = self._tracer.get_tracer("bioetl.processor").start_as_current_span(
            name, attributes=attrs
        )
        span.__enter__()
        return span

    def _end_span(self, span: Span, error: Exception | None = None) -> None:
        """End a tracing span."""
        if not span:
            return
        if error:
            span.set_attribute("error", True)
            span.record_exception(error)
        span.__exit__(None, None, None)
