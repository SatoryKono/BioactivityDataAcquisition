"""Base transformer exceptions."""

from __future__ import annotations

from bioetl.domain.exceptions.base import DataQualityError
from bioetl.domain.types import JsonDict


class TransformationError(DataQualityError):
    """Raised when a transformation fails due to missing/invalid data."""

    def __init__(self, message: str, field: str | None = None) -> None:
        super().__init__(message)
        self.field = field

class FilteredOutError(DataQualityError):
    """Raised when a record is excluded by Silver filters."""

    def __init__(
        self,
        reason: str = "Record excluded by silver filters",
        *,
        details: JsonDict | None = None,
    ) -> None:
        super().__init__(reason)
        self.details = details or {}
