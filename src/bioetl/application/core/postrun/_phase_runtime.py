"""Shared phase runtime helpers for ``PostrunService``."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from contextlib import AbstractContextManager
from typing import TYPE_CHECKING, Literal

from bioetl.application.observability.span_attribute_values import (
    coerce_span_attribute_value,
)

if TYPE_CHECKING:
    from opentelemetry.trace import Span

    from bioetl.domain.ports import LoggerPort, MetricsPort
from bioetl.application.core.postrun._phase_descriptions import (
    PostrunLogLevel,
    PostrunPhaseCompletion,
)

PostrunPhaseName = Literal[
    "compaction",
    "dq_evaluation",
    "dq_reports",
    "vacuum",
    "final_metadata",
]

def resolve_postrun_phase_log_level(status: str) -> PostrunLogLevel:
    """Map bounded postrun statuses to structured log levels."""
    if status == "failed":
        return "error"
    if status == "warning":
        return "warning"
    return "info"

def emit_postrun_phase_observability(
    *,
    metrics: MetricsPort,
    logger: LoggerPort,
    pipeline_name: str,
    phase_events_metric: str,
    phase_duration_metric: str,
    phase: PostrunPhaseName,
    status: str,
    duration_seconds: float,
    level: PostrunLogLevel | None = None,
    **extra: object,
) -> None:
    """Emit bounded metrics and logs for one postrun subphase."""
    labels = {
        "pipeline": pipeline_name,
        "phase": phase,
        "status": status,
    }
    metrics.increment_counter(
        phase_events_metric,
        1,
        labels=labels,
    )
    metrics.observe_histogram(
        phase_duration_metric,
        duration_seconds,
        labels=labels,
    )

    resolved_level = level or resolve_postrun_phase_log_level(status)
    log_payload: dict[str, object] = {
        "phase": phase,
        "status": status,
        "duration_seconds": round(duration_seconds, 4),
        **extra,
    }
    if resolved_level == "error":
        logger.error("postrun_phase_completed", **log_payload)
    elif resolved_level == "warning":
        logger.warning("postrun_phase_completed", **log_payload)
    else:
        logger.info("postrun_phase_completed", **log_payload)

async def run_async_postrun_phase[ResultT](
    *,
    span_factory: Callable[[str], AbstractContextManager[Span]],
    phase: PostrunPhaseName,
    operation: Callable[[], Awaitable[ResultT]],
    operation_errors: tuple[type[BaseException], ...],
    emit_phase_observability: Callable[..., None],
    on_success: Callable[[ResultT], PostrunPhaseCompletion],
) -> ResultT:
    """Run one async postrun phase with consistent tracing and failure handling."""
    start_time = time.perf_counter()
    with span_factory(f"postrun.{phase}") as span:
        try:
            result = await operation()
        except operation_errors as exc:
            emit_phase_observability(
                phase=phase,
                status="failed",
                duration_seconds=time.perf_counter() - start_time,
                level="error",
                error_type=type(exc).__name__,
            )
            raise
        completion = on_success(result)
        for key, value in completion.span_attributes.items():
            span.set_attribute(key, coerce_span_attribute_value(value))
        emit_phase_observability(
            phase=phase,
            status=completion.status,
            duration_seconds=time.perf_counter() - start_time,
            level=completion.level,
            **completion.observability_fields,
        )
        return result

def run_sync_postrun_phase[ResultT](
    *,
    span_factory: Callable[[str], AbstractContextManager[Span]],
    phase: PostrunPhaseName,
    operation: Callable[[], ResultT],
    operation_errors: tuple[type[BaseException], ...],
    emit_phase_observability: Callable[..., None],
    on_success: Callable[[ResultT], PostrunPhaseCompletion],
) -> ResultT:
    """Run one sync postrun phase with consistent tracing and failure handling."""
    start_time = time.perf_counter()
    with span_factory(f"postrun.{phase}") as span:
        try:
            result = operation()
        except operation_errors as exc:
            emit_phase_observability(
                phase=phase,
                status="failed",
                duration_seconds=time.perf_counter() - start_time,
                level="error",
                error_type=type(exc).__name__,
            )
            raise
        completion = on_success(result)
        for key, value in completion.span_attributes.items():
            span.set_attribute(key, coerce_span_attribute_value(value))
        emit_phase_observability(
            phase=phase,
            status=completion.status,
            duration_seconds=time.perf_counter() - start_time,
            level=completion.level,
            **completion.observability_fields,
        )
        return result
