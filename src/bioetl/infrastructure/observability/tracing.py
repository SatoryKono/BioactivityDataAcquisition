"""Tracing helpers for measuring execution spans."""

from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Iterator

from bioetl.interfaces.observability import (
    LoggingPortABC,
    MetricsPortABC,
    TracingPortABC,
)


@contextmanager
def with_tracing_span(
    name: str,
    *,
    logger: LoggingPortABC | None = None,
    tracer: TracingPortABC | None = None,
    metrics: MetricsPortABC | None = None,
    trace_id: str | None = None,
) -> Iterator[None]:
    """Measure execution duration and emit structured observability signals."""

    span = tracer.start_span(name) if tracer else None
    bound_logger = logger.apply_bind(stage=name) if logger else None
    context: dict[str, str] = {"stage": name}
    if trace_id:
        context["trace_id"] = trace_id
    start = time.perf_counter()
    if bound_logger:
        bound_logger.info("span_start", **context)
    error: Exception | None = None
    try:
        yield
    except Exception as exc:  # noqa: B902 - re-raising original exception
        error = exc
        duration = time.perf_counter() - start
        if bound_logger:
            bound_logger.error(
                "span_error", duration_sec=duration, error=str(exc), **context
            )
        raise
    finally:
        duration = time.perf_counter() - start
        if metrics:
            metrics.observe_histogram(
                "stage_duration_seconds", duration, {"stage": name}
            )
        if bound_logger:
            bound_logger.info(
                "span_finish",
                duration_sec=duration,
                outcome="error" if error else "success",
                **context,
            )
        if tracer and span:
            tracer.end_span(span)


__all__ = ["with_tracing_span"]
