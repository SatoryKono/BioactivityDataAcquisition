"""Core record source interfaces and helpers.

This module defines the abstract interface for record sources (RecordSourceABC)
and the SourceRecord value object. Concrete implementations that involve
orchestration logic are located in the application layer.

See also:
    - bioetl.application.sources.ApiRecordSource: API-based record source
    - bioetl.application.files: File-based record sources

Terminology:
    SourceRecord: A record extracted from a data source before normalization.
    RawRecord: Deprecated alias for SourceRecord (will be removed in v3.0).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import TYPE_CHECKING
import warnings

from pydantic import BaseModel, ConfigDict


class SourceRecord(BaseModel):
    """Record extracted from a data source before normalization.

    This is the canonical name for raw records in the domain model.
    """

    model_config = ConfigDict(extra="allow")


def __getattr__(name: str):
    """Module-level __getattr__ for deprecation warnings."""
    if name == "RawRecord":
        warnings.warn(
            "RawRecord is deprecated, use SourceRecord instead. "
            "Will be removed in v3.0.",
            DeprecationWarning,
            stacklevel=2,
        )
        return SourceRecord
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# Type alias for backward compatibility
# TODO: Remove in v3.0
if TYPE_CHECKING:
    RawRecord = SourceRecord


class RecordSourceABC(ABC):
    """Abstract base class for record sources returning record batches."""

    @abstractmethod
    def iter_records(self) -> Iterable[list[SourceRecord]]:
        """Return iterable over source record batches as lists of mappings."""


class InMemoryRecordSource(RecordSourceABC):
    """Simple record source backed by an in-memory list."""

    def __init__(
        self,
        records: list[SourceRecord],
        chunk_size: int | None = None,
    ):
        self._records = list(records)
        self._chunk_size = chunk_size

    def iter_records(self) -> Iterable[list[SourceRecord]]:
        """Yield in-memory records in configured chunk sizes."""
        if self._chunk_size is None or self._chunk_size <= 0:
            yield self._records[:]
            return

        for start in range(0, len(self._records), self._chunk_size):
            yield self._records[start : start + self._chunk_size]


# Type alias for backward compatibility
RecordSource = RecordSourceABC
