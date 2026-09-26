"""Helpers for deterministic runtime timestamp assembly."""

from __future__ import annotations

import time
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from bioetl.application.runtime_clock import resolve_runtime_clock

if TYPE_CHECKING:
    from bioetl.domain.ports import ClockPort

__all__ = [
    "capture_runtime_timing_anchor",
    "derive_completion_timestamp",
]


def capture_runtime_timing_anchor(
    *,
    clock: ClockPort | None,
    started_at: datetime | None = None,
) -> tuple[datetime, float]:
    """Capture the wall-clock anchor and monotonic start for one execution."""
    wall_clock_anchor = started_at
    if wall_clock_anchor is None:
        wall_clock_anchor = resolve_runtime_clock(clock).now()
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
