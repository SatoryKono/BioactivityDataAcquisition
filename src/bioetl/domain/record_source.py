"""Core record source interfaces and helpers.

This module defines the abstract interface for record sources (RecordSourceABC)
and the RawRecord value object. Concrete implementations that involve
orchestration logic are located in the application layer.

See also:
    - bioetl.application.sources.ApiRecordSource: API-based record source
    - bioetl.application.files: File-based record sources
"""

from __future__ import annotations

import warnings
from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Any

from pydantic import BaseModel, ConfigDict


class RawRecord(BaseModel):
    """Raw record model before normalization."""

    model_config = ConfigDict(extra="allow")


class RecordSourceABC(ABC):
    """Abstract base class for record sources returning record batches."""

    @abstractmethod
    def iter_records(self) -> Iterable[list[RawRecord]]:
        """Return iterable over raw record batches as lists of mappings."""


class InMemoryRecordSource(RecordSourceABC):
    """Simple record source backed by an in-memory list."""

    def __init__(self, records: list[RawRecord], chunk_size: int | None = None):
        self._records = list(records)
        self._chunk_size = chunk_size

    def iter_records(self) -> Iterable[list[RawRecord]]:
        """Yield in-memory records in configured chunk sizes."""
        if self._chunk_size is None or self._chunk_size <= 0:
            yield self._records[:]
            return

        for start in range(0, len(self._records), self._chunk_size):
            yield self._records[start : start + self._chunk_size]


def __getattr__(name: str) -> Any:
    """Provide backward compatibility for ApiRecordSource import.

    This function allows importing ApiRecordSource from the old location
    while emitting a deprecation warning.

    Args:
        name: The attribute name being accessed.

    Returns:
        The ApiRecordSource class from its new location.

    Raises:
        AttributeError: If the requested attribute is not ApiRecordSource.
    """
    if name == "ApiRecordSource":
        warnings.warn(
            "Importing ApiRecordSource from bioetl.domain.record_source is deprecated. "
            "Use 'from bioetl.application.sources import ApiRecordSource' instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        from bioetl.application.sources import ApiRecordSource

        return ApiRecordSource
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
