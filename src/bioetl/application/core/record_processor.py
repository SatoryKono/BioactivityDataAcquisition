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
from bioetl.application.core._record_processor_write_support import (
    write_gold_layer,
    write_silver_layer,
)
from bioetl.application.core.batch_executor import BatchResult

if TYPE_CHECKING:
    from bioetl.application.batch_processing_contracts import LayerWriteOutcome
    from bioetl.application.core.batch_metrics import BatchMetricsRecorderService
    from bioetl.application.core.batch_transformer import (
        BatchTransformer,
        TransformResult,
    )
    from bioetl.application.core.batch_writer import BatchWriter
    from bioetl.application.core.quarantine_manager import QuarantineRuntimeService
    from bioetl.application.core.record_processor_config import RecordProcessorConfig
    from bioetl.application.observability.domain_event_emitter import (
        DomainEventEmitterProtocol,
    )
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.ports import TracingPort
    from bioetl.domain.types import BatchID
    from bioetl.domain.value_objects.bronze_result import BronzeWriteResult


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
        quarantine_manager: QuarantineRuntimeService | None = None,
        domain_event_emitter: DomainEventEmitterProtocol | None = None,
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
            quarantine_manager: Optional manager for write-stage quarantine parity.
            domain_event_emitter: Optional structured event sink for quarantines.
            When collaborators are
                provided, schema-violating Silver/Gold records are quarantined
                with the same semantics as ``safe_write_layer``; when omitted,
                schema violations propagate (legacy behavior).
        """
        self._context = context
        self._config = config
        span_executor = span_executor_factory(tracer)
        self._span_executor = span_executor
        self._batch_metrics = batch_metrics
        self._transformer = transformer
        self._writer = writer
        self._quarantine_manager = quarantine_manager
        self._domain_event_emitter = domain_event_emitter

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
        self._batch_metrics.track_processed_records(
            "quarantined", result.quarantined_count
        )
        typed_bronze_result = cast("BronzeWriteResult | None", bronze_result)
        bronze_refs = [typed_bronze_result] if typed_bronze_result else None
        silver_outcome = await self._write_silver_layer(
            result=result,
            batch_id=batch_id,
            ingestion_ts=ingestion_ts,
            bronze_refs=bronze_refs,
        )
        self._batch_metrics.track_processed_records(
            "silver", silver_outcome.confirmed_count
        )
        gold_outcome = await self._write_gold_layer(
            result=result,
            batch_id=batch_id,
            silver_outcome=silver_outcome,
        )
        self._batch_metrics.track_processed_records(
            "gold", gold_outcome.confirmed_count
        )
        write_quarantined = (
            silver_outcome.quarantined_count + gold_outcome.quarantined_count
        )
        if write_quarantined:
            self._batch_metrics.track_processed_records(
                "quarantined", write_quarantined
            )
        return BatchResult(
            bronze_count=len(records),
            silver_count=silver_outcome.confirmed_count,
            gold_count=gold_outcome.confirmed_count,
            quarantined_count=result.quarantined_count + write_quarantined,
        )

    async def _write_silver_layer(
        self,
        *,
        result: TransformResult,
        batch_id: BatchID,
        ingestion_ts: datetime,
        bronze_refs: list[BronzeWriteResult] | None,
    ) -> LayerWriteOutcome:
        """Write Silver with quarantine parity when a manager is configured."""
        return await write_silver_layer(
            span_executor=self._span_executor,
            writer=self._writer,
            quarantine_manager=self._quarantine_manager,
            logger=self._context.logger,
            run_id=self._context.run_id,
            domain_event_emitter=self._domain_event_emitter,
            result=result,
            batch_id=batch_id,
            ingestion_ts=ingestion_ts,
            bronze_refs=bronze_refs,
        )

    async def _write_gold_layer(
        self,
        *,
        result: TransformResult,
        batch_id: BatchID,
        silver_outcome: LayerWriteOutcome,
    ) -> LayerWriteOutcome:
        """Write Gold after Silver; blocked when Silver was quarantined."""
        return await write_gold_layer(
            span_executor=self._span_executor,
            writer=self._writer,
            quarantine_manager=self._quarantine_manager,
            logger=self._context.logger,
            run_id=self._context.run_id,
            domain_event_emitter=self._domain_event_emitter,
            result=result,
            batch_id=batch_id,
            ingestion_ts=self._context.started_at,
            silver_outcome=silver_outcome,
        )
