"""Metrics and tracing helpers for checkpoint save operations."""

from __future__ import annotations

__all__ = [
    "close_checkpoint_save_span",
    "emit_checkpoint_save_event",
    "observe_checkpoint_save_duration",
    "start_checkpoint_save_span",
]

from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from opentelemetry.trace import Span

    from bioetl.domain.ports import MetricsPort, TracingPort

CHECKPOINT_TRACER_NAME = "bioetl.checkpoint"


def emit_checkpoint_save_event(
    metrics: MetricsPort | None,
    pipeline_name: str,
    *,
    operation: str,
    status: str,
) -> None:
    """Emit the checkpoint save counter event when metrics are configured."""
    if metrics is None:
        return
    metrics.increment_counter(
        "bioetl_checkpoint_save_events_total",
        1,
        {
            "pipeline": pipeline_name,
            "operation": operation,
            "status": status,
        },
    )


def observe_checkpoint_save_duration(
    metrics: MetricsPort | None,
    pipeline_name: str,
    *,
    operation: str,
    status: str,
    duration_seconds: float,
) -> None:
    """Record checkpoint save duration when metrics are configured."""
    if metrics is None:
        return
    metrics.observe_histogram(
        "bioetl_checkpoint_save_duration_seconds",
        duration_seconds,
        {
            "pipeline": pipeline_name,
            "operation": operation,
            "status": status,
        },
    )


def start_checkpoint_save_span(
    tracer: TracingPort | None,
    pipeline_name: str,
    *,
    operation: str,
    records_processed: int,
) -> Span | None:
    """Open the checkpoint save span when a tracer is configured."""
    if tracer is None:
        return None
    span = cast(
        "Span",
        cast(
            object,
            tracer.get_tracer(CHECKPOINT_TRACER_NAME).start_as_current_span(
                "checkpoint_save",
                attributes={
                    "bioetl.pipeline": pipeline_name,
                    "bioetl.checkpoint.operation": operation,
                    "bioetl.checkpoint.scope": "ordinary",
                    "bioetl.checkpoint.records_processed": records_processed,
                },
            ),
        ),
    )
    span.__enter__()
    return span


def close_checkpoint_save_span(
    span: Span | None,
    *,
    status: str,
    error: BaseException | None = None,
) -> None:
    """Close the checkpoint save span with its terminal status."""
    if span is None:
        return
    span.set_attribute("bioetl.checkpoint.status", status)
    if error is not None:
        span.set_attribute("error", True)
        span.set_attribute("error.type", type(error).__name__)
        if isinstance(error, Exception):
            span.record_exception(error)
    span.__exit__(None, None, None)
