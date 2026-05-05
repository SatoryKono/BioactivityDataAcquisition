"""Unit tests for SystemClock infrastructure adapter."""

from __future__ import annotations

from datetime import UTC, datetime

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
def test_system_clock_now_uses_system_timestamp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SystemClock.now converts the current POSIX timestamp to UTC."""
    clock = SystemClock()
    expected = datetime(2024, 1, 15, 12, 0, tzinfo=UTC)
    fixed_timestamp = expected.timestamp()
    monkeypatch.setattr(
        "bioetl.infrastructure.time.system_clock.time.time", lambda: fixed_timestamp
    )

    assert clock.now() == expected
