"""Shared deterministic time helpers for domain execution contexts."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Protocol

MISSING_RUNTIME_TIMESTAMP = datetime(1970, 1, 1, tzinfo=UTC)
"""Deterministic sentinel for compatibility-only direct context construction."""


class ClockLike(Protocol):
    """Minimal clock seam required by domain context factories."""

    def now(self) -> datetime:
        """Return the current timestamp."""
        ...


def resolve_context_started_at(
    *,
    started_at: datetime | None,
    clock: ClockLike | None,
) -> datetime:
    """Resolve replay-sensitive context time through explicit inputs first."""
    if started_at is not None:
        return started_at
    if clock is not None:
        return clock.now()
    return MISSING_RUNTIME_TIMESTAMP


def resolve_manifest_created_at(
    *,
    clock: ClockLike | None,
    created_at_factory: Callable[[], datetime] | None,
) -> datetime:
    """Resolve manifest creation time through the configured clock/factory seam."""
    if clock is not None:
        return clock.now()
    if created_at_factory is not None:
        return created_at_factory()
    return MISSING_RUNTIME_TIMESTAMP


def utc_instant(value: datetime) -> datetime:
    """Compare aware instants without changing their identity representation."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(UTC)


def validate_completion_order(
    completed_at: datetime | None,
    started_at: datetime,
) -> None:
    """Reject missing time zones and completion before the starting UTC instant."""
    start = utc_instant(started_at)
    if completed_at is None:
        return
    if utc_instant(completed_at) >= start:
        return
    raise ValueError(
        "completed_at cannot be earlier than started_at: "
        f"started_at={started_at!s}, completed_at={completed_at!s}"
    )
