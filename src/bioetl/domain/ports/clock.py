"""Clock port for UTC timestamp creation."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol


class ClockPort(Protocol):
    """Port providing current UTC timestamp."""

    def now_utc(self) -> datetime:
        """Return timezone-aware UTC datetime."""
