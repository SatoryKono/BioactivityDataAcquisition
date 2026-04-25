"""Runtime helper functions for composite runner support logic."""

from __future__ import annotations

__all__ = ["run_seed", "save_checkpoint_safe"]

import time
from typing import TYPE_CHECKING, cast

from bioetl.application.composite.checkpoint import CompositeCheckpointState
from bioetl.application.composite.runner_pkg.runner_constants import (
    CHECKPOINT_NON_FATAL_ERRORS,
)
from bioetl.application.composite.runner_pkg.runner_support_types import (
    _CompositeRunnerSupportHostProtocol,
)
from bioetl.application.runtime_timestamps import (
    capture_runtime_timing_anchor,
    derive_completion_timestamp,
)
from bioetl.domain.composite.result import SeedResult
from bioetl.domain.exceptions import BioETLError

if TYPE_CHECKING:
    from opentelemetry.trace import Span

    from bioetl.domain.ports import TracingPort


_CHECKPOINT_TRACER_NAME = "bioetl.checkpoint"


def _emit_checkpoint_save_event(
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


def _observe_checkpoint_save_duration(
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


def _start_checkpoint_save_span(
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


def _close_checkpoint_save_span(
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


async def save_checkpoint_safe(
    host: _CompositeRunnerSupportHostProtocol,
    state: CompositeCheckpointState,
    operation: str,
) -> bool:
    """Save checkpoint with graceful error handling."""
    started_at = time.monotonic()
    span = _start_checkpoint_save_span(host, operation=operation)
    try:
        await host._checkpoint_manager.save(state)
        duration_seconds = time.monotonic() - started_at
        _emit_checkpoint_save_event(
            host,
            operation=operation,
            status="succeeded",
        )
        _observe_checkpoint_save_duration(
            host,
            operation=operation,
            status="succeeded",
            duration_seconds=duration_seconds,
        )
        _close_checkpoint_save_span(
            host,
            span,
            status="succeeded",
        )
        return True
    except CHECKPOINT_NON_FATAL_ERRORS as error:
        duration_seconds = time.monotonic() - started_at
        _emit_checkpoint_save_event(
            host,
            operation=operation,
            status="failed",
        )
        _observe_checkpoint_save_duration(
            host,
            operation=operation,
            status="failed",
            duration_seconds=duration_seconds,
        )
        _close_checkpoint_save_span(
            host,
            span,
            status="failed",
            error=error,
        )
        host._logger.warning(
            "checkpoint_save_failed",
            **host._build_correlation_log_context(
                operation=operation,
                error=str(error),
                error_type=type(error).__name__,
                note="Resume capability may be affected",
            ),
        )
        return False
    except BioETLError as error:
        duration_seconds = time.monotonic() - started_at
        _emit_checkpoint_save_event(
            host,
            operation=operation,
            status="failed",
        )
        _observe_checkpoint_save_duration(
            host,
            operation=operation,
            status="failed",
            duration_seconds=duration_seconds,
        )
        _close_checkpoint_save_span(
            host,
            span,
            status="failed",
            error=error,
        )
        host._logger.warning(
            "checkpoint_save_failed",
            **host._build_correlation_log_context(
                operation=operation,
                error=str(error),
                error_type=type(error).__name__,
                reason_code="unexpected_bioetl_error",
                note="Resume capability may be affected",
            ),
        )
        return False


async def run_seed(host: _CompositeRunnerSupportHostProtocol) -> SeedResult:
    """Run the seed pipeline and normalize its metrics into SeedResult."""
    host._logger.info(
        "Running seed pipeline",
        **host._build_correlation_log_context(
            stage="seed",
            seed_pipeline=host._config.seed.pipeline,
        ),
    )

    started_at, started_monotonic = capture_runtime_timing_anchor(
        clock=getattr(host, "_clock", None)
    )
    runner = host._seed_runner_factory()
    await runner.run()
    completed_at, duration_seconds = derive_completion_timestamp(
        started_at=started_at,
        started_monotonic=started_monotonic,
    )

    metrics = runner.execution_metrics
    records_extracted = int(metrics["records_fetched"])
    records_silver = int(metrics["records_silver"])

    return SeedResult(
        pipeline_name=host._config.seed.pipeline,
        records_extracted=records_extracted,
        records_silver=records_silver,
        keys_generated=records_silver,
        duration_seconds=duration_seconds,
        started_at=started_at,
        completed_at=completed_at,
    )
