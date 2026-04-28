"""Clock test utilities."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

FIXED_TEST_TIME = datetime(2026, 4, 28, 12, 0, tzinfo=UTC)


class FixedClock:
    """Deterministic clock that always returns the same timestamp."""

    def __init__(self, value: datetime) -> None:
        self._value = value

    def now(self) -> datetime:
        """Return fixed timestamp."""
        return self._value


class StepClock:
    """Deterministic clock that advances by fixed step on each call."""

    def __init__(self, start: datetime, step: timedelta) -> None:
        self._current = start
        self._step = step

    def now(self) -> datetime:
        """Return current timestamp and move clock forward."""
        current = self._current
        self._current = self._current + self._step
        return current


def fixed_test_clock() -> FixedClock:
    """Return the canonical deterministic clock shared across unit suites."""
    return FixedClock(FIXED_TEST_TIME)


__all__ = ["FIXED_TEST_TIME", "FixedClock", "StepClock", "fixed_test_clock"]
