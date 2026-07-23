"""Checkpoint loading and warning helpers for composite checkpoint orchestration."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from bioetl.application.composite.checkpoint.state import CompositeCheckpointState
from bioetl.application.runtime_clock import resolve_runtime_clock
from bioetl.domain.exceptions import BioETLError, StorageError
from bioetl.domain.ports import CompositeCheckpointPort, LoggerPort, MetricsPort

if TYPE_CHECKING:
    from bioetl.domain.ports import ClockPort

CHECKPOINT_READ_ERRORS = (
    json.JSONDecodeError,
    KeyError,
    OSError,
    TypeError,
    ValueError,
    StorageError,
)
CHECKPOINT_WRITE_ERRORS = (
    OSError,
    TypeError,
    ValueError,
    StorageError,
)


def latest_checkpoint_filename(
    *,
    storage: CompositeCheckpointPort,
    glob_pattern: str,
) -> str | None:
    """Return the newest checkpoint filename matching the storage glob."""
    matches = storage.list_glob(glob_pattern)
    if len(matches) <= 1:
        return matches[0] if matches else None
    ranked: list[tuple[datetime, str]] = []
    for path in matches:
        try:
            payload = storage.read(path)
            state = CompositeCheckpointState.from_dict(json.loads(payload))
            stamp = state.updated_at or state.created_at
            if stamp is not None:
                ranked.append((_as_utc_comparable(stamp), path))
        except (CHECKPOINT_READ_ERRORS, BioETLError):
            continue
    if ranked:
        try:
            return max(ranked, key=lambda item: (item[0], item[1]))[1]
        except TypeError:
            # Mixed naive/aware timestamps: fall back to deterministic filename order.
            return sorted(matches)[-1]
    return sorted(matches)[-1]


def _as_utc_comparable(value: datetime) -> datetime:
    """Normalize timestamps so naive/aware values can be ordered safely."""
    if value.tzinfo is None:
        # Treat naive timestamps as UTC for deterministic ranking only.
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _emit_checkpoint_saved_at_from_state(
    *,
    metrics: MetricsPort | None,
    composite_name: str,
    state: CompositeCheckpointState,
) -> None:
    """Publish the latest persisted checkpoint timestamp when the state carries one."""
    if metrics is None:
        return
    saved_at = state.updated_at or state.created_at
    if saved_at is None:
        return
    metrics.set_gauge(
        "bioetl_checkpoint_saved_at_seconds",
        saved_at.timestamp(),
        {"pipeline": composite_name},
    )


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


def resolve_resume_checkpoint_filename(
    *,
    storage: CompositeCheckpointPort,
    checkpoint_filename: str,
    glob_pattern: str,
) -> str | None:
    """Resolve the explicit or latest available checkpoint filename for resume."""
    if storage.exists(checkpoint_filename):
        return checkpoint_filename
    return latest_checkpoint_filename(storage=storage, glob_pattern=glob_pattern)


def load_checkpoint_state(
    *,
    storage: CompositeCheckpointPort,
    logger: LoggerPort,
    composite_name: str,
    filename: str,
    metrics: MetricsPort | None = None,
) -> CompositeCheckpointState | None:
    """Load and parse one checkpoint state from storage if it exists."""
    try:
        content = storage.read(filename)
        if content is None:
            return None
        data = json.loads(content)
        state = CompositeCheckpointState.from_dict(data)
        raw_state = data.get("state")
        if raw_state is not None and state.state.value != raw_state:
            logger.warning(
                "Checkpoint state value corrupted, using default",
                composite=composite_name,
                raw_state=raw_state,
                parsed_state=state.state.value,
            )
        logger.info(
            "Loaded checkpoint",
            composite=composite_name,
            checkpoint_path=filename,
            state=state.state.value,
            seed_completed=state.seed_completed,
            completed_enrichers=list(state.completed_enrichers),
            last_event_id=state.last_event_id,
            last_event_occurred_at=(
                state.last_event_occurred_at.isoformat()
                if state.last_event_occurred_at is not None
                else None
            ),
        )
        _emit_checkpoint_saved_at_from_state(
            metrics=metrics,
            composite_name=composite_name,
            state=state,
        )
        if metrics is not None:
            metrics.increment_counter(
                "bioetl_checkpoint_load_events_total",
                1,
                {
                    "pipeline": composite_name,
                    "status": "loaded",
                },
            )
        return state
    except CHECKPOINT_READ_ERRORS as error:
        logger.warning(
            "Failed to load checkpoint",
            composite=composite_name,
            error=str(error),
            error_type=type(error).__name__,
            reason_code="checkpoint_load_failed",
        )
        if metrics is not None:
            metrics.increment_counter(
                "bioetl_checkpoint_load_events_total",
                1,
                {
                    "pipeline": composite_name,
                    "status": "failed",
                },
            )
    except BioETLError as error:
        logger.warning(
            "Failed to load checkpoint",
            composite=composite_name,
            error=str(error),
            error_type=type(error).__name__,
            reason_code="unexpected_bioetl_error",
        )
        if metrics is not None:
            metrics.increment_counter(
                "bioetl_checkpoint_load_events_total",
                1,
                {
                    "pipeline": composite_name,
                    "status": "failed",
                },
            )
    return None
