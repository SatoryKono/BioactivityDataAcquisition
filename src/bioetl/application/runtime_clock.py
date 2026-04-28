"""Application-local default implementation for runtime ClockPort wiring."""

from __future__ import annotations

import time
from datetime import UTC, datetime

from bioetl.domain.ports import ClockPort

__all__ = ["RuntimeClock", "resolve_runtime_clock"]


class RuntimeClock(ClockPort):
    """ClockPort implementation used when legacy application constructors omit one."""

    def now(self) -> datetime:
        """Return current UTC time through the ClockPort seam."""
        return datetime.fromtimestamp(time.time(), UTC)


def resolve_runtime_clock(clock: ClockPort | None) -> ClockPort:
    """Return an explicit runtime clock for application services."""
    return clock or RuntimeClock()
