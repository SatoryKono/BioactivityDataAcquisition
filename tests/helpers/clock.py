"""Clock test utilities."""

from __future__ import annotations

from datetime import datetime, timedelta


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


__all__ = ["FixedClock", "StepClock"]
