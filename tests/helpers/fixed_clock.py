"""Deterministic clock for tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, tzinfo

from bioetl.domain.ports import ClockPort


class FixedClock(ClockPort):
    """Clock test double with controllable time progression."""

    def __init__(self, initial: datetime) -> None:
        self._current = (
            initial if initial.tzinfo is not None else initial.replace(tzinfo=UTC)
        )

    def now_utc(self) -> datetime:
        return self._current.astimezone(UTC)

    def now(self, timezone: tzinfo = UTC) -> datetime:
        return self._current.astimezone(timezone)

    def tick(self, *, seconds: int = 0) -> None:
        self._current = self._current + timedelta(seconds=seconds)
