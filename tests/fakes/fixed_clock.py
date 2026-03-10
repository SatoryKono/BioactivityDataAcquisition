"""Fixed clock fake for deterministic tests."""

from __future__ import annotations

from datetime import datetime

from bioetl.domain.ports import ClockPort


class FixedClock(ClockPort):
    """Clock fake that always returns predefined timestamp."""

    def __init__(self, now: datetime) -> None:
        self._now = now

    def now_utc(self) -> datetime:
        return self._now
