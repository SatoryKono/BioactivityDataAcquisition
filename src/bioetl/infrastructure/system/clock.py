"""System clock adapter."""

from __future__ import annotations

from datetime import UTC, datetime, tzinfo

from bioetl.domain.ports import ClockPort


class SystemClock(ClockPort):
    """Clock adapter backed by system time."""

    def now_utc(self) -> datetime:
        return datetime.now(tz=UTC)

    def now(self, timezone: tzinfo = UTC) -> datetime:
        return datetime.now(tz=timezone)
