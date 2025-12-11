"""Infrastructure implementation of TimestampProvider."""

from __future__ import annotations

from datetime import datetime, timezone

from bioetl.domain.transform.contracts import TimestampProviderABC


class DeterministicTimestampProvider(TimestampProviderABC):
    """Deterministic timestamp provider.

    Fixes time at initialization and returns it for all calls.
    This ensures determinism within a single data processing session.
    """

    def __init__(self, fixed_time: datetime | None = None) -> None:
        """Initialize provider.

        Args:
            fixed_time: Fixed timestamp. If not specified,
                        current time (UTC) is used.
        """
        if fixed_time is None:
            self._time = datetime.now(timezone.utc)
        else:
            # Ensure timezone awareness
            if fixed_time.tzinfo is None:
                self._time = fixed_time.replace(tzinfo=timezone.utc)
            else:
                self._time = fixed_time

    def get_extraction_timestamp(self) -> datetime:
        """Return fixed data extraction timestamp."""
        return self._time


__all__ = ["DeterministicTimestampProvider"]
