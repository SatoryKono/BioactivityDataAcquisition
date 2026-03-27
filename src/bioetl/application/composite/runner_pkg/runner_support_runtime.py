"""Runtime helper functions for composite runner support logic."""

from __future__ import annotations

__all__ = ["run_seed", "save_checkpoint_safe"]

from datetime import UTC, datetime

from bioetl.application.composite.checkpoint import CompositeCheckpointState
from bioetl.application.composite.runner_pkg.runner_constants import (
    CHECKPOINT_NON_FATAL_ERRORS,
)
from bioetl.application.composite.runner_pkg.runner_support_types import (
    _CompositeRunnerSupportHostProtocol,
)
from bioetl.domain.composite.result import SeedResult
from bioetl.domain.exceptions import BioETLError


async def save_checkpoint_safe(
    host: _CompositeRunnerSupportHostProtocol,
    state: CompositeCheckpointState,
    operation: str,
) -> bool:
    """Save checkpoint with graceful error handling."""
    try:
        await host._checkpoint_manager.save(state)
        return True
    except CHECKPOINT_NON_FATAL_ERRORS as error:
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

    started_at = datetime.now(tz=UTC)
    runner = host._seed_runner_factory()
    await runner.run()
    completed_at = datetime.now(tz=UTC)

    metrics = runner.execution_metrics
    records_extracted = int(metrics["records_fetched"])
    records_silver = int(metrics["records_silver"])

    return SeedResult(
        pipeline_name=host._config.seed.pipeline,
        records_extracted=records_extracted,
        records_silver=records_silver,
        keys_generated=records_silver,
        duration_seconds=(completed_at - started_at).total_seconds(),
        started_at=started_at,
        completed_at=completed_at,
    )
