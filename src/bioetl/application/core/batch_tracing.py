"""Batch tracing orchestration for ETL pipeline observability."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from bioetl.application.core._batch_tracing_support import (
    add_memory_decision_trace_events,
    build_batch_span_attributes,
    build_execution_span_attributes,
    build_layer_span_attributes,
    set_execution_stats_attributes,
    set_memory_decision_trace_attributes,
    set_record_result_attributes,
)
from bioetl.application.core.pipeline_span_lifecycle import (
    close_span,
    close_span_with_shutdown,
)
from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from opentelemetry.trace import Span

    from bioetl.application.core.pipeline_span_lifecycle import _ClosableSpan
    from bioetl.application.core.record_processor_config import RecordProcessorConfig
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.ports import TracingPort
    from bioetl.domain.types import BatchID


class BatchTracingManagerService:
    """Manage execution, batch, and layer spans for pipeline runs."""

    TRACER_NAME = "bioetl.batch_executor"

    def __init__(
        self,
        tracer: TracingPort | None,
        context: PipelineContext,
        config: RecordProcessorConfig,
        initial_batch_size: int,
        adaptive_sizing_enabled: bool,
    ) -> None:
        """Initialize the tracing manager with explicit tracer injection."""
        if tracer is None:
            raise TypeError(
                "BatchTracingManagerService requires explicit tracer injection. "
                "Build NoOpTracing in composition or test support when needed."
            )
        self._tracer = tracer
        self._context = context
        self._config = config
        self._initial_batch_size = initial_batch_size
        self._adaptive_sizing_enabled = adaptive_sizing_enabled

    def start_execution_span(self) -> Span | None:
        """Start the root pipeline execution span."""
        otel_tracer = self._tracer.get_tracer(self.TRACER_NAME)
        span = cast(
            Span,  # OpenTelemetry span context manager is unparameterized at runtime
            otel_tracer.start_as_current_span(
                "pipeline_execution",
                attributes=cast(dict[str, object], build_execution_span_attributes(
                    pipeline_name=self._config.pipeline_name,
                    entity_type=self._config.entity_type,
                    context=self._context,
                    adaptive_batch_sizing_enabled=self._adaptive_sizing_enabled,
                    initial_batch_size=self._initial_batch_size,
                )),
            ),
        )
        span.__enter__()
        return span

    def start_batch_span(
        self, batch_id: BatchID, record_count: int, start_index: int
    ) -> Span | None:
        """Start a tracing span for one batch."""
        otel_tracer = self._tracer.get_tracer(self.TRACER_NAME)
        span = cast(
            Span,  # OpenTelemetry span context manager is unparameterized at runtime
            otel_tracer.start_as_current_span(
                f"batch_{batch_id}",
                attributes=cast(dict[str, object], build_batch_span_attributes(
                    batch_id=batch_id,
                    record_count=record_count,
                    run_type=self._context.run_type.value,
                    entity_type=self._config.entity_type,
                    start_index=start_index,
                )),
            ),
        )
        span.__enter__()
        return span

    def start_layer_span(
        self,
        name: str,
        batch_id: BatchID,
        count: int,
        input_count: bool = False,
    ) -> Span:
        """Start a tracing span for one layer operation."""
        span = cast(
            Span,  # OpenTelemetry span context manager is unparameterized at runtime
            self._tracer.get_tracer(self.TRACER_NAME).start_as_current_span(
                name,
                attributes=cast(dict[str, object], build_layer_span_attributes(
                    batch_id=batch_id,
                    count=count,
                    input_count=input_count,
                )),
            ),
        )
        span.__enter__()
        return span

    def set_execution_stats(
        self,
        span: Span | None,
        *,
        total_fetched: int,
        total_bronze: int,
        total_silver: int,
        total_gold: int,
        total_quarantined: int,
        batch_size_reductions: int,
        min_batch_size_used: int,
        memory_decision_trace: tuple[JsonDict, ...],
    ) -> None:
        """Set final execution statistics on the root span."""
        if not span:
            return
        set_execution_stats_attributes(
            span,
            total_fetched=total_fetched,
            total_bronze=total_bronze,
            total_silver=total_silver,
            total_gold=total_gold,
            total_quarantined=total_quarantined,
            batch_size_reductions=batch_size_reductions,
            min_batch_size_used=min_batch_size_used,
        )
        set_memory_decision_trace_attributes(
            span,
            memory_decision_trace=memory_decision_trace,
        )
        add_memory_decision_trace_events(
            span,
            memory_decision_trace=memory_decision_trace,
        )

    def set_batch_result(
        self,
        span: Span | None,
        *,
        bronze_count: int,
        silver_count: int,
        gold_count: int,
        quarantined_count: int,
    ) -> None:
        """Set batch result counters on a batch span."""
        if not span:
            return
        set_record_result_attributes(
            span,
            bronze_count=bronze_count,
            silver_count=silver_count,
            gold_count=gold_count,
            quarantined_count=quarantined_count,
        )

    def set_transform_result(
        self,
        span: Span | None,
        *,
        silver_count: int,
        gold_count: int,
        quarantined_count: int,
    ) -> None:
        """Set transform result counters on a transform span."""
        if not span:
            return
        set_record_result_attributes(
            span,
            silver_count=silver_count,
            gold_count=gold_count,
            quarantined_count=quarantined_count,
        )

    def end_span(self, span: Span | None, error: Exception | None = None) -> None:
        """End a tracing span and optionally record an error."""
        close_span(cast("_ClosableSpan | None", span), error)

    def end_span_with_shutdown(self, span: Span | None) -> None:
        """End a tracing span with shutdown markers."""
        close_span_with_shutdown(cast("_ClosableSpan | None", span))


__all__ = ["BatchTracingManagerService"]
