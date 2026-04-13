"""Helpers for deterministic runtime timestamp assembly."""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta

__all__ = [
    "capture_runtime_timing_anchor",
    "derive_completion_timestamp",
]


def capture_runtime_timing_anchor(
    *,
    started_at: datetime | None = None,
) -> tuple[datetime, float]:
    """Capture the wall-clock anchor and monotonic start for one execution."""
    return (started_at or datetime.now(tz=UTC), time.monotonic())


def derive_completion_timestamp(
    *,
    started_at: datetime,
    started_monotonic: float,
    completed_monotonic: float | None = None,
) -> tuple[datetime, float]:
    """Derive a completion timestamp from a captured wall-clock anchor."""
    ended_monotonic = (
        time.monotonic() if completed_monotonic is None else completed_monotonic
    )
    duration_seconds = max(0.0, ended_monotonic - started_monotonic)
    return started_at + timedelta(seconds=duration_seconds), duration_seconds
