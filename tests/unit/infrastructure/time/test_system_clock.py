"""Unit tests for SystemClock infrastructure adapter."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from bioetl.domain.ports import ClockPort
from bioetl.infrastructure.time import SystemClock


@pytest.mark.unit
def test_system_clock_implements_clock_port() -> None:
    """SystemClock satisfies ClockPort contract."""
    clock = SystemClock()
    assert isinstance(clock, ClockPort)


@pytest.mark.unit
def test_system_clock_returns_utc_aware_datetime() -> None:
    """SystemClock.now returns timezone-aware UTC datetime."""
    clock = SystemClock()
    value = clock.now()

    assert isinstance(value, datetime)
    assert value.tzinfo is UTC


@pytest.mark.unit
def test_system_clock_now_is_current_time() -> None:
    """SystemClock.now returns value close to current UTC time."""
    clock = SystemClock()
    before = datetime.now(UTC)
    value = clock.now()
    after = datetime.now(UTC)

    assert before - timedelta(seconds=1) <= value <= after + timedelta(seconds=1)
