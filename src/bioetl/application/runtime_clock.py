"""Application-local runtime ClockPort helpers."""

from __future__ import annotations

from datetime import UTC, datetime

from bioetl.domain.ports import ClockPort

__all__ = ["RuntimeClock", "resolve_runtime_clock"]


class RuntimeClockService(ClockPort):
    """Explicit system ClockPort implementation for runtime wiring."""

    def now(self) -> datetime:
        """Return current UTC time through the ClockPort seam."""
        return datetime.now(UTC)


RuntimeClock = RuntimeClockService


def resolve_runtime_clock(clock: ClockPort | None) -> ClockPort:
    """Return the explicit runtime clock required by application services."""
    if clock is None:
        raise RuntimeError(
            "ClockPort is required for runtime timestamp generation; "
            "system-time fallbacks are not allowed."
        )
    return clock
