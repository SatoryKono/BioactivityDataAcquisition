"""Warning helpers for composite checkpoint load and overwrite paths."""

from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING

from bioetl.application.composite.checkpoint._checkpoint_runtime import (
    CHECKPOINT_READ_ERRORS,
    _emit_checkpoint_saved_at_from_state,
    latest_checkpoint_filename,
)
from bioetl.application.composite.checkpoint.state import CompositeCheckpointState
from bioetl.application.runtime_clock import resolve_runtime_clock
from bioetl.domain.exceptions import BioETLError
from bioetl.domain.ports import CompositeCheckpointPort, LoggerPort, MetricsPort

if TYPE_CHECKING:
    from bioetl.domain.ports import ClockPort

__all__ = [
    "warn_if_checkpoint_exists_with_progress",
    "warn_if_checkpoint_stale",
]


def warn_if_checkpoint_exists_with_progress(
    *,
    storage: CompositeCheckpointPort,
    logger: LoggerPort,
    composite_name: str,
    glob_pattern: str,
    metrics: MetricsPort | None = None,
) -> None:
    """Warn when an existing resumable checkpoint would be overwritten."""
    latest = latest_checkpoint_filename(storage=storage, glob_pattern=glob_pattern)
    if latest is None or not storage.exists(latest):
        return

    try:
        content = storage.read(latest)
        if content is None:
            return
        state = CompositeCheckpointState.from_dict(json.loads(content))
        _emit_checkpoint_saved_at_from_state(
            metrics=metrics,
            composite_name=composite_name,
            state=state,
        )
        if state.is_resumable:
            logger.warning(
                "Existing checkpoint with progress will be overwritten",
                composite=composite_name,
                checkpoint_path=latest,
                checkpoint_state=state.state.value,
                seed_completed=state.seed_completed,
                completed_enrichers=len(state.completed_enrichers),
                hint="Use --resume flag to continue from previous progress",
            )
    except CHECKPOINT_READ_ERRORS as error:
        logger.debug(
            "Checkpoint exists but cannot be parsed, will be overwritten",
            composite=composite_name,
            checkpoint_path=latest,
            error=str(error),
            error_type=type(error).__name__,
            reason_code="checkpoint_read_failed",
        )
    except BioETLError as error:
        logger.warning(
            "Checkpoint pre-check failed with domain error",
            composite=composite_name,
            checkpoint_path=latest,
            error=str(error),
            error_type=type(error).__name__,
            reason_code="unexpected_bioetl_error",
        )


def warn_if_checkpoint_stale(
    *,
    logger: LoggerPort,
    composite_name: str,
    stale_threshold_hours: float,
    state: CompositeCheckpointState,
    clock: ClockPort | None = None,
    reference_time: datetime | None = None,
) -> None:
    """Warn when resume targets a checkpoint older than the configured threshold."""
    if stale_threshold_hours <= 0:
        return
    ref_time = state.updated_at or state.created_at
    if ref_time is None:
        return

    current_time = reference_time
    if current_time is None:
        current_time = resolve_runtime_clock(clock).now()
    age = current_time - ref_time
    if age.total_seconds() <= stale_threshold_hours * 3600:
        return

    logger.warning(
        "Resuming from stale checkpoint",
        composite=composite_name,
        checkpoint_age_hours=round(age.total_seconds() / 3600, 1),
        threshold_hours=stale_threshold_hours,
        checkpoint_updated_at=ref_time.isoformat(),
        checkpoint_state=state.state.value,
        reason_code="stale_checkpoint_resume",
        hint="Seed data may have been overwritten since this checkpoint was saved",
    )
