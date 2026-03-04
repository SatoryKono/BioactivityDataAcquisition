"""Clock port for time access abstraction."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable


@runtime_checkable
class ClockPort(Protocol):
    """Port for obtaining current time."""

    def now(self) -> datetime:
        """Return current timezone-aware UTC datetime."""
        ...


__all__ = ["ClockPort"]
