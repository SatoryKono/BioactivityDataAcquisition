"""Unit tests for clock test helpers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from bioetl.domain.ports import ClockPort
from tests.helpers.clock import FixedClock, StepClock


@pytest.mark.unit
def test_fixed_clock_returns_same_value_on_every_call() -> None:
    """FixedClock always returns configured timestamp."""
    value = datetime(2026, 3, 4, 12, 0, 0, tzinfo=UTC)
    clock = FixedClock(value)

    assert clock.now() == value
    assert clock.now() == value
    assert isinstance(clock, ClockPort)


@pytest.mark.unit
def test_step_clock_advances_by_step() -> None:
    """StepClock increments timestamp by configured step."""
    start = datetime(2026, 3, 4, 12, 0, 0, tzinfo=UTC)
    step = timedelta(seconds=30)
    clock = StepClock(start=start, step=step)

    assert clock.now() == start
    assert clock.now() == start + step
    assert clock.now() == start + step * 2
    assert isinstance(clock, ClockPort)
