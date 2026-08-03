"""Checkpoint saved-at timestamp payload and metric helpers."""

from __future__ import annotations

from bioetl.domain.ports import ClockPort, MetricsPort
from bioetl.domain.types import JsonDict
from bioetl.domain.types.checkpoint_metadata import CheckpointMetadata


def set_checkpoint_saved_at(
    metrics: MetricsPort | None,
    *,
    pipeline_name: str,
    checkpoint_saved_at_epoch_seconds: float | int | str | None,
) -> None:
    """Publish the latest persisted checkpoint timestamp when available."""
    if metrics is None or checkpoint_saved_at_epoch_seconds is None:
        return
    try:
        value = float(checkpoint_saved_at_epoch_seconds)
    except (TypeError, ValueError):
        return
    metrics.set_gauge(
        "bioetl_checkpoint_saved_at_seconds",
        value,
        {"pipeline": pipeline_name},
    )


def checkpoint_saved_at_epoch_seconds(clock: ClockPort | None) -> float | None:
    """Return checkpoint persistence time from the runtime clock when provided."""
    if clock is None:
        return None
    return float(clock.now().timestamp())


def metadata_with_checkpoint_saved_at(
    metadata: CheckpointMetadata,
    *,
    clock: ClockPort | None,
) -> JsonDict:
    """Convert checkpoint metadata and attach deterministic clock-owned save time."""
    payload = metadata.to_dict()
    checkpoint_saved_at = checkpoint_saved_at_epoch_seconds(clock)
    if checkpoint_saved_at is not None:
        payload.setdefault("checkpoint_saved_at_epoch_seconds", checkpoint_saved_at)
    return payload


__all__ = [
    "checkpoint_saved_at_epoch_seconds",
    "metadata_with_checkpoint_saved_at",
    "set_checkpoint_saved_at",
]
