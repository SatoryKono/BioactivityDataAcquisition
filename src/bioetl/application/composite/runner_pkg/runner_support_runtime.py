"""Runtime helper functions for composite runner support logic."""

from __future__ import annotations

__all__ = ["run_seed", "save_checkpoint_safe"]

import time

from bioetl.application.composite.checkpoint import CompositeCheckpointState
from bioetl.application.composite.runner_pkg.runner_checkpoint_save_observability import (
    checkpoint_saved_at_epoch_seconds,
    close_checkpoint_save_span,
    emit_checkpoint_save_event,
    observe_checkpoint_save_duration,
    set_checkpoint_saved_at,
    start_checkpoint_save_span,
)
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


async def save_checkpoint_safe(
    host: _CompositeRunnerSupportHostProtocol,
    state: CompositeCheckpointState,
    operation: str,
) -> bool:
    """Save checkpoint with graceful error handling."""
    started_at = time.monotonic()
    span = start_checkpoint_save_span(host, operation=operation)
    try:
        await host._checkpoint_manager.save(state)
        duration_seconds = time.monotonic() - started_at
        emit_checkpoint_save_event(
            host,
            operation=operation,
            status="succeeded",
        )
        set_checkpoint_saved_at(host, checkpoint_saved_at_epoch_seconds(host))
        observe_checkpoint_save_duration(
            host,
            operation=operation,
            status="succeeded",
            duration_seconds=duration_seconds,
        )
        close_checkpoint_save_span(
            host,
            span,
            status="succeeded",
        )
        return True
    except CHECKPOINT_NON_FATAL_ERRORS as error:
        duration_seconds = time.monotonic() - started_at
        emit_checkpoint_save_event(
            host,
            operation=operation,
            status="failed",
        )
        observe_checkpoint_save_duration(
            host,
            operation=operation,
            status="failed",
            duration_seconds=duration_seconds,
        )
        close_checkpoint_save_span(
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
        emit_checkpoint_save_event(
            host,
            operation=operation,
            status="failed",
        )
        observe_checkpoint_save_duration(
            host,
            operation=operation,
            status="failed",
            duration_seconds=duration_seconds,
        )
        close_checkpoint_save_span(
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
