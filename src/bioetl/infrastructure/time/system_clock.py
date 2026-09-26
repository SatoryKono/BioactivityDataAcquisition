"""System clock adapter implementation."""

from __future__ import annotations

import time
from datetime import UTC, datetime


class SystemClock:
    """Clock adapter backed by the system UTC time."""

    def now(self) -> datetime:
        """Return current UTC datetime.

        Returns:
            Current UTC datetime with timezone info.
        """
        return datetime.fromtimestamp(time.time(), UTC)


def current_utc_time() -> datetime:
    """Return current UTC time through the infrastructure system clock adapter."""
    return SystemClock().now()


__all__ = ["SystemClock", "current_utc_time"]
