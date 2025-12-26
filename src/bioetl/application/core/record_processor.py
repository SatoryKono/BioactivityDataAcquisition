"""Orchestrates batch processing through Bronze, Silver, and Gold layers.

Observability: Nested spans for transform → write_bronze → write_silver → write_gold.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from bioetl.application.core.batch_metrics import BatchMetricsRecorder
from bioetl.application.core.batch_transformer import BatchTransformer, TransformResult
from bioetl.application.core.batch_writer import BatchWriter
from bioetl.application.core.quarantine_manager import QuarantineManager

if TYPE_CHECKING:
    from bioetl.application.core.config import RecordProcessorConfig
    from bioetl.application.core.pipeline_services import PipelineServices
    from bioetl.application.core.protocols import (
        GoldFilterCallback,
        GoldTransformCallback,
        TransformCallback,
    )
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.error_classifier import ErrorClassifier
    from bioetl.domain.ports import GoldValidatorPort, TracingPort
    from bioetl.domain.types import BatchID


@dataclass(frozen=True, slots=True)
class BatchResult:
    """Result of processing a batch of records."""

    bronze_count: int
    silver_count: int
    gold_count: int
    quarantined_count: int


class RecordProcessor:
    """Orchestrates batch transformation and writing across all layers."""

    def __init__(
        self,
        services: PipelineServices,
        error_classifier: ErrorClassifier,
        context: PipelineContext,
        config: RecordProcessorConfig,
        transform_callback: TransformCallback,
        gold_filter_callback: GoldFilterCallback,
        gold_transform_callback: GoldTransformCallback,
        gold_validator: GoldValidatorPort,
        tracer: TracingPort | None = None,
    ):
        self._context = context
        self._tracer = tracer

        pipeline_label = f"{config.provider}_{config.entity_type}"
        self._batch_metrics = BatchMetricsRecorder(
            services.metrics, pipeline_label, context.run_type.value
        )

        self._transformer = BatchTransformer(
            context=context,
            config=config,
            error_classifier=error_classifier,
            quarantine_manager=QuarantineManager(
                quarantine_port=services.quarantine,
                pipeline_name=config.pipeline_name,
            ),
            batch_metrics=self._batch_metrics,
            transform_callback=transform_callback,
            gold_filter_callback=gold_filter_callback,
            gold_transform_callback=gold_transform_callback,
        )

        self._writer = BatchWriter(
            storage=services.storage,
            context=context,
            config=config,
            gold_validator=gold_validator,
            error_classifier=error_classifier,
            batch_metrics=self._batch_metrics,
        )

    async def process_batch(
        self, records: list[dict[str, Any]], batch_id: BatchID
    ) -> BatchResult:
        """Process batch through Bronze -> Silver -> Gold with tracing."""
        ingestion_ts = self._context.started_at

        # Write to Bronze
        await self._execute_with_span(
            "write_bronze",
            self._writer.write_bronze(records, batch_id, ingestion_ts),
            batch_id, len(records),
            on_error=lambda e: self._writer.log_and_track_write_error("bronze", e, batch_id),
        )
        self._batch_metrics.track_batch_size("bronze", len(records))
        self._batch_metrics.track_processed_records("bronze", len(records))

        # Transform records
        result = await self._execute_transform_with_span(records, batch_id)
        self._batch_metrics.track_processed_records("quarantined", result.quarantined_count)
        self._batch_metrics.track_processed_records("silver", len(result.silver_records))
        self._batch_metrics.track_processed_records("gold", len(result.gold_records))

        # Write to Silver
        if result.silver_records:
            await self._execute_with_span(
                "write_silver",
                self._writer.write_silver(result.silver_records, batch_id, ingestion_ts),
                batch_id, len(result.silver_records),
                on_error=lambda e: self._writer.log_and_track_write_error("silver", e, batch_id),
            )

        # Write to Gold
        if result.gold_records:
            await self._execute_with_span(
                "write_gold",
                self._writer.write_gold(result.gold_records),
                batch_id, len(result.gold_records),
                on_error=lambda e: self._writer.log_and_track_write_error("gold", e, batch_id),
            )

        return BatchResult(
            bronze_count=len(records),
            silver_count=len(result.silver_records),
            gold_count=len(result.gold_records),
            quarantined_count=result.quarantined_count,
        )

    async def _execute_with_span(
        self, name: str, coro: Any, batch_id: BatchID, count: int, on_error: Any = None
    ) -> Any:
        """Execute coroutine with tracing span."""
        span = self._start_span(name, batch_id, count)
        try:
            result = await coro
            self._end_span(span)
            return result
        except Exception as e:
            self._end_span(span, e)
            if on_error:
                on_error(e)
            raise

    async def _execute_transform_with_span(
        self, records: list[dict[str, Any]], batch_id: BatchID
    ) -> TransformResult:
        """Execute transformation with extended span attributes."""
        span = self._start_span("transform", batch_id, len(records), input_count=True)
        try:
            result = await self._transformer.transform_batch(records, batch_id)
            if span:
                span.set_attribute("bioetl.silver_count", len(result.silver_records))
                span.set_attribute("bioetl.gold_count", len(result.gold_records))
                span.set_attribute("bioetl.quarantined_count", result.quarantined_count)
            self._end_span(span)
            return result
        except Exception as e:
            self._end_span(span, e)
            raise

    def _start_span(
        self, name: str, batch_id: BatchID, count: int, input_count: bool = False
    ) -> Any:
        """Start a tracing span if tracer is available."""
        if not self._tracer:
            return None
        count_key = "bioetl.input_count" if input_count else "bioetl.record_count"
        attrs = {"bioetl.batch_id": str(batch_id), count_key: count}
        span = self._tracer.get_tracer("bioetl.processor").start_as_current_span(name, attributes=attrs)
        span.__enter__()
        return span

    def _end_span(self, span: Any, error: Exception | None = None) -> None:
        """End a tracing span."""
        if not span:
            return
        if error:
            span.set_attribute("error", True)
            span.record_exception(error)
        span.__exit__(None, None, None)
