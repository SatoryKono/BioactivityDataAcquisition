"""Batch Tracing Manager for ETL pipeline observability.

Extracted from BatchExecutor to reduce class size and improve separation of concerns.
Handles all OpenTelemetry span management for batch processing operations.

Responsibilities:
- Create and manage root execution spans
- Create per-batch spans with proper nesting
- Create per-layer spans (transform, write_bronze, write_silver, write_gold)
- Record span attributes and exceptions
- Handle span lifecycle (enter/exit/error)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bioetl.domain.ports import NoOpTracing

if TYPE_CHECKING:
    from bioetl.application.core.config import RecordProcessorConfig
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.ports import TracingPort
    from bioetl.domain.types import BatchID


class BatchTracingManager:
    """Manages tracing spans for batch ETL operations.

    Provides methods to create, configure, and close OpenTelemetry spans
    for pipeline execution, batch processing, and layer operations.

    All methods are safe to call with NoOpTracing - they return None spans
    that are safely ignored throughout the codebase.
    """

    TRACER_NAME = "bioetl.batch_executor"

    def __init__(
        self,
        tracer: TracingPort | None,
        context: PipelineContext,
        config: RecordProcessorConfig,
        initial_batch_size: int,
        adaptive_sizing_enabled: bool,
    ) -> None:
        """Initialize batch tracing manager.

        Args:
            tracer: OpenTelemetry tracer port. If None, uses NoOpTracing.
            context: Pipeline execution context.
            config: Record processor configuration.
            initial_batch_size: Initial batch size for tracking.
            adaptive_sizing_enabled: Whether adaptive batch sizing is enabled.

        """
        self._tracer: TracingPort = tracer if tracer is not None else NoOpTracing()
        self._context = context
        self._config = config
        self._initial_batch_size = initial_batch_size
        self._adaptive_sizing_enabled = adaptive_sizing_enabled

    def start_execution_span(self) -> Any | None:
        """Start root tracing span for pipeline execution.

        Returns:
            OpenTelemetry span context or None if tracing disabled.

        """
        otel_tracer = self._tracer.get_tracer(self.TRACER_NAME)
        span = otel_tracer.start_as_current_span(
            "pipeline_execution",
            attributes={
                "bioetl.pipeline": self._config.pipeline_name or "unknown",
                "bioetl.run_id": str(self._context.run_id),
                "bioetl.entity_type": self._config.entity_type,
                "bioetl.run_type": self._context.run_type.value,
                "bioetl.adaptive_batch_sizing": self._adaptive_sizing_enabled,
                "bioetl.initial_batch_size": self._initial_batch_size,
            },
        )
        span.__enter__()
        return span

    def start_batch_span(
        self, batch_id: BatchID, record_count: int, start_index: int
    ) -> Any | None:
        """Start tracing span for a batch.

        Args:
            batch_id: Unique identifier for the batch.
            record_count: Number of records in the batch.
            start_index: Starting index of records in this batch.

        Returns:
            OpenTelemetry span context or None if tracing disabled.

        """
        otel_tracer = self._tracer.get_tracer(self.TRACER_NAME)
        span = otel_tracer.start_as_current_span(
            f"batch_{batch_id}",
            attributes={
                "bioetl.batch_id": str(batch_id),
                "bioetl.record_count": record_count,
                "bioetl.run_type": self._context.run_type.value,
                "bioetl.entity_type": self._config.entity_type,
                "bioetl.start_index": start_index,
            },
        )
        span.__enter__()
        return span

    def start_layer_span(
        self,
        name: str,
        batch_id: BatchID,
        count: int,
        input_count: bool = False,
    ) -> Any:
        """Start a tracing span for a layer operation.

        Args:
            name: Name of the layer operation (e.g., "write_bronze", "transform").
            batch_id: Unique identifier for the batch.
            count: Number of records for this operation.
            input_count: If True, use "input_count" attribute; else "record_count".

        Returns:
            OpenTelemetry span context.

        """
        count_key = "bioetl.input_count" if input_count else "bioetl.record_count"
        attrs = {"bioetl.batch_id": str(batch_id), count_key: count}
        span = self._tracer.get_tracer(self.TRACER_NAME).start_as_current_span(
            name, attributes=attrs
        )
        span.__enter__()
        return span

    def set_execution_stats(
        self,
        span: Any | None,
        *,
        total_fetched: int,
        total_bronze: int,
        total_silver: int,
        total_gold: int,
        total_quarantined: int,
        batch_size_reductions: int,
        min_batch_size_used: int,
    ) -> None:
        """Set final statistics on the execution span.

        Args:
            span: The execution span to update.
            total_fetched: Total records fetched from source.
            total_bronze: Total records written to Bronze.
            total_silver: Total records written to Silver.
            total_gold: Total records written to Gold.
            total_quarantined: Total records quarantined.
            batch_size_reductions: Number of batch size reductions.
            min_batch_size_used: Minimum batch size used during execution.

        """
        if not span:
            return

        span.set_attribute("bioetl.total_fetched", total_fetched)
        span.set_attribute("bioetl.total_bronze", total_bronze)
        span.set_attribute("bioetl.total_silver", total_silver)
        span.set_attribute("bioetl.total_gold", total_gold)
        span.set_attribute("bioetl.total_quarantined", total_quarantined)
        span.set_attribute("bioetl.batch_size_reductions", batch_size_reductions)
        span.set_attribute("bioetl.min_batch_size_used", min_batch_size_used)

    def set_batch_result(
        self,
        span: Any | None,
        *,
        bronze_count: int,
        silver_count: int,
        gold_count: int,
        quarantined_count: int,
    ) -> None:
        """Set batch result attributes on span.

        Args:
            span: The batch span to update.
            bronze_count: Records written to Bronze.
            silver_count: Records written to Silver.
            gold_count: Records written to Gold.
            quarantined_count: Records quarantined.

        """
        if not span:
            return

        span.set_attribute("bioetl.bronze_count", bronze_count)
        span.set_attribute("bioetl.silver_count", silver_count)
        span.set_attribute("bioetl.gold_count", gold_count)
        span.set_attribute("bioetl.quarantined_count", quarantined_count)

    def set_transform_result(
        self,
        span: Any | None,
        *,
        silver_count: int,
        gold_count: int,
        quarantined_count: int,
    ) -> None:
        """Set transform result attributes on span.

        Args:
            span: The transform span to update.
            silver_count: Records transformed to Silver.
            gold_count: Records transformed to Gold.
            quarantined_count: Records quarantined during transform.

        """
        if not span:
            return

        span.set_attribute("bioetl.silver_count", silver_count)
        span.set_attribute("bioetl.gold_count", gold_count)
        span.set_attribute("bioetl.quarantined_count", quarantined_count)

    def end_span(self, span: Any | None, error: Exception | None = None) -> None:
        """End a tracing span.

        Args:
            span: The span to end.
            error: Optional exception to record on the span.

        """
        if not span:
            return
        if error:
            span.set_attribute("error", True)
            span.record_exception(error)
        span.__exit__(None, None, None)

    def end_span_with_shutdown(self, span: Any | None) -> None:
        """End span marking it as shutdown.

        Args:
            span: The span to end with shutdown marker.

        """
        if span:
            span.set_attribute("bioetl.shutdown", True)
            span.__exit__(None, None, None)


__all__ = ["BatchTracingManager"]
