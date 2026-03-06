"""Base transformer exceptions."""

from __future__ import annotations


class TransformationError(Exception):
    """Raised when a transformation fails due to missing/invalid data."""

    def __init__(self, message: str, field: str | None = None) -> None:
        super().__init__(message)
        self.field = field


class FilteredOutError(Exception):
    """Raised when a record is excluded by Silver filters."""

    def __init__(self, reason: str = "Record excluded by silver filters") -> None:
        super().__init__(reason)
