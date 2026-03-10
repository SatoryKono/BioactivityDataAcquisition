"""System clock adapter implementation."""

from __future__ import annotations

from datetime import UTC, datetime

from bioetl.domain.ports import ClockPort


class SystemClock(ClockPort):
    """Clock adapter backed by system UTC time."""

    def now(self) -> datetime:
        """Return current UTC timestamp."""
        return datetime.now(tz=UTC)
