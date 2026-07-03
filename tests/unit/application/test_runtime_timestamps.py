from __future__ import annotations

from datetime import UTC, datetime

import pytest

from bioetl.application.runtime_clock import resolve_runtime_clock
from bioetl.application.runtime_timestamps import capture_runtime_timing_anchor
from tests.helpers.clock import FixedClock


@pytest.mark.unit
def test_resolve_runtime_clock_requires_explicit_clock() -> None:
    with pytest.raises(RuntimeError, match="ClockPort is required"):
        resolve_runtime_clock(None)


@pytest.mark.unit
def test_capture_runtime_timing_anchor_requires_clock_when_started_at_missing() -> None:
    with pytest.raises(RuntimeError, match="ClockPort is required"):
        capture_runtime_timing_anchor(clock=None)


@pytest.mark.unit
def test_capture_runtime_timing_anchor_uses_explicit_clock() -> None:
    started_at, started_monotonic = capture_runtime_timing_anchor(
        clock=FixedClock(datetime(2026, 4, 28, 12, 0, tzinfo=UTC))
    )

    assert started_at == datetime(2026, 4, 28, 12, 0, tzinfo=UTC)
    assert started_monotonic >= 0.0
