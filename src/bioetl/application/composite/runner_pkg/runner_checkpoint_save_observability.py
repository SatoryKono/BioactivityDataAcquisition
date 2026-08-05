"""Checkpoint-save metrics and span helpers for composite runner support."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from bioetl.application.composite.runner_pkg.runner_support_types import (
    _CompositeRunnerSupportHostProtocol,
)

if TYPE_CHECKING:
    from opentelemetry.trace import Span

    from bioetl.domain.ports import TracingPort

_CHECKPOINT_TRACER_NAME = "bioetl.checkpoint"

__all__ = [
    "checkpoint_saved_at_epoch_seconds",
    "close_checkpoint_save_span",
    "emit_checkpoint_save_event",
    "observe_checkpoint_save_duration",
    "set_checkpoint_saved_at",
    "start_checkpoint_save_span",
]


def emit_checkpoint_save_event(
    host: _CompositeRunnerSupportHostProtocol,
    *,
    operation: str,
    status: str,
) -> None:
    metrics = getattr(host, "_metrics", None)
    if metrics is None:
        return
    metrics.increment_counter(
        "bioetl_checkpoint_save_events_total",
        1,
        {
            "pipeline": host._config.name,
            "operation": operation,
            "status": status,
        },
    )


def observe_checkpoint_save_duration(
    host: _CompositeRunnerSupportHostProtocol,
    *,
    operation: str,
    status: str,
    duration_seconds: float,
) -> None:
    metrics = getattr(host, "_metrics", None)
    if metrics is None:
        return
    metrics.observe_histogram(
        "bioetl_checkpoint_save_duration_seconds",
        duration_seconds,
        {
            "pipeline": host._config.name,
            "operation": operation,
            "status": status,
        },
    )


def set_checkpoint_saved_at(
    host: _CompositeRunnerSupportHostProtocol,
    checkpoint_saved_at_epoch_seconds: float | None,
) -> None:
    metrics = getattr(host, "_metrics", None)
    if metrics is None or checkpoint_saved_at_epoch_seconds is None:
        return
    metrics.set_gauge(
        "bioetl_checkpoint_saved_at_seconds",
        checkpoint_saved_at_epoch_seconds,
        {"pipeline": host._config.name},
    )


def checkpoint_saved_at_epoch_seconds(
    host: _CompositeRunnerSupportHostProtocol,
) -> float | None:
    clock = getattr(host, "_clock", None)
    if clock is None:
        return None
    return float(clock.now().timestamp())


def start_checkpoint_save_span(
    host: _CompositeRunnerSupportHostProtocol,
    *,
    operation: str,
) -> Span | None:
    tracer = cast("TracingPort | None", getattr(host, "_tracing", None))
    if tracer is None:
        return None
    span = cast(
        "Span",
        tracer.get_tracer(_CHECKPOINT_TRACER_NAME).start_as_current_span(
            "checkpoint_save",
            attributes={
                "bioetl.pipeline": host._config.name,
                "bioetl.checkpoint.operation": operation,
                "bioetl.checkpoint.scope": "composite",
            },
        ),
    )
    span.__enter__()
    return span


def close_checkpoint_save_span(
    host: _CompositeRunnerSupportHostProtocol,
    span: Span | None,
    *,
    status: str,
    error: BaseException | None = None,
) -> None:
    if span is None:
        return
    span.set_attribute("bioetl.checkpoint.status", status)
    if error is not None:
        span.set_attribute("error", True)
        span.set_attribute("error.type", type(error).__name__)
        if isinstance(error, Exception):
            span.record_exception(error)
    span.__exit__(None, None, None)
    tracer = cast("TracingPort | None", getattr(host, "_tracing", None))
    if tracer is not None:
        tracer.flush()
