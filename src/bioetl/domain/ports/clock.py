"""Clock port for deterministic time access."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable


@runtime_checkable
class ClockPort(Protocol):
    """Port for retrieving current time.

    Enables deterministic tests by injecting fake/fixed clock implementations.
    """

    def now(self) -> datetime:
        """Return current timestamp."""
