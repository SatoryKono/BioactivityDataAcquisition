"""System clock adapter for production runtime."""

from __future__ import annotations

from datetime import UTC, datetime

from bioetl.domain.ports import ClockPort


class SystemClock(ClockPort):
    """Clock adapter returning current system UTC time."""

    def now_utc(self) -> datetime:
        """Return timezone-aware current UTC datetime."""
        return datetime.now(tz=UTC)
