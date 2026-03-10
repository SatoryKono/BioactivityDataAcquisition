"""Clock bootstrap helpers."""

from __future__ import annotations

from bioetl.domain.ports import ClockPort
from bioetl.infrastructure.system import SystemClock


def bootstrap_clock_port() -> ClockPort:
    """Create default system clock adapter."""
    return SystemClock()
