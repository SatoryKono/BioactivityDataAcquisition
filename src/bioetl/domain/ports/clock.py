"""Clock abstraction port for deterministic time handling."""

from __future__ import annotations

from datetime import UTC, datetime, tzinfo
from typing import Protocol


class ClockPort(Protocol):
    """Port for retrieving current time.

    Allows injecting deterministic time sources in application services.
    """

    def now_utc(self) -> datetime:
        """Return current UTC-aware datetime."""

    def now(self, timezone: tzinfo = UTC) -> datetime:
        """Return current timezone-aware datetime."""
