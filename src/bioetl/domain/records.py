"""Record-level domain protocols and type aliases."""
from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import Any, Protocol, TypeAlias


RawRecord: TypeAlias = dict[str, Any]
"""Unnormalized record payload returned by sources."""

NormalizedRecord: TypeAlias = dict[str, Any]
"""Record payload after normalization and schema alignment."""


class RecordSource(Protocol):
    """Protocol for streaming raw records from an input source."""

    def iter_records(self) -> Iterator[RawRecord]:
        """Return an iterator yielding raw records."""

    def metadata(self) -> dict[str, Any]:
        """Return optional metadata about the source (release, path, etc.)."""


class NormalizationService(Protocol):
    """Protocol for record-level normalization."""

    def normalize(self, record: RawRecord) -> NormalizedRecord:
        """Normalize a single raw record to the canonical shape."""

    def normalize_many(self, records: Iterable[RawRecord]) -> Iterable[NormalizedRecord]:
        """Normalize multiple raw records preserving order."""


__all__ = [
    "RawRecord",
    "NormalizedRecord",
    "RecordSource",
    "NormalizationService",
]
