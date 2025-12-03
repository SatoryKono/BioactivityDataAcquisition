"""Core record source interfaces and helpers."""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Protocol, TypedDict

from bioetl.domain.contracts import ExtractionServiceABC


class RawRecord(TypedDict, total=False):
    """Raw record type before normalization."""

    # Arbitrary key/value mapping for raw provider payloads
    ...


class RecordSource(Protocol):
    """Protocol for record sources."""

    def iter_records(self) -> Iterable[RawRecord]:
        """Return iterable over raw records."""


class InMemoryRecordSource(RecordSource):
    """Simple record source backed by an in-memory list."""

    def __init__(self, records: list[RawRecord]):
        self._records = list(records)

    def iter_records(self) -> Iterable[RawRecord]:
        return list(self._records)


class ApiRecordSource(RecordSource):
    """Record source that fetches data from an extraction service."""

    def __init__(
        self,
        extraction_service: ExtractionServiceABC,
        entity: str,
        filters: dict[str, Any] | None = None,
    ) -> None:
        self._extraction_service = extraction_service
        self._entity = entity
        self._filters = filters or {}

    def iter_records(self) -> Iterable[RawRecord]:
        df = self._extraction_service.extract_all(self._entity, **self._filters)
        return df.to_dict(orient="records")
