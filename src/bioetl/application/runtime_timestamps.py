"""Helpers for deterministic runtime timestamp assembly."""

from __future__ import annotations

import time
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from bioetl.domain.context import current_utc_time

if TYPE_CHECKING:
    from bioetl.domain.ports import ClockPort

__all__ = [
    "capture_runtime_timing_anchor",
    "derive_completion_timestamp",
]


def capture_runtime_timing_anchor(
    *,
    started_at: datetime | None = None,
    clock: ClockPort | None = None,
) -> tuple[datetime, float]:
    """Capture the wall-clock anchor and monotonic start for one execution."""
    wall_clock_anchor = started_at
    if wall_clock_anchor is None:
        wall_clock_anchor = clock.now() if clock is not None else current_utc_time()
    return wall_clock_anchor, time.monotonic()


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
