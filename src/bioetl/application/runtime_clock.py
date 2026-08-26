"""Application-local runtime ClockPort helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.ports import ClockPort

__all__ = ["RuntimeClock", "current_utc_time", "resolve_runtime_clock"]


class RuntimeClockService:
    """Explicit system ClockPort implementation for runtime wiring."""

    def now(self) -> datetime:
        """Return current UTC time through the ClockPort seam."""
        return datetime.now(UTC)


RuntimeClock = RuntimeClockService


def current_utc_time() -> datetime:
    """Return current UTC time through the application runtime clock seam."""
    return RuntimeClock().now()


def resolve_runtime_clock(clock: ClockPort | None) -> ClockPort:
    """Return the explicit runtime clock required by application services."""
    if clock is None:
        raise RuntimeError(
            "ClockPort is required for runtime timestamp generation; "
            "system-time fallbacks are not allowed."
        )
    return clock
