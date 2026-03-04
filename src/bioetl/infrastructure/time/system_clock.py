"""System clock adapter implementation."""

from __future__ import annotations

import time
from datetime import UTC, datetime

from bioetl.domain.ports import ClockPort


class SystemClock(ClockPort):
    """Clock adapter backed by the system UTC time."""

    def now(self) -> datetime:
        """Return current UTC datetime."""
        return datetime.fromtimestamp(time.time(), UTC)


__all__ = ["SystemClock"]
