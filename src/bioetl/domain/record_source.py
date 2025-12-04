"""Core record source interfaces and helpers."""
from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import Any, Protocol, TypedDict

import pandas as pd

from bioetl.domain.contracts import ExtractionServiceABC


class RawRecord(TypedDict, total=False):
    """Raw record type before normalization."""

    # Arbitrary key/value mapping for raw provider payloads
    ...


class RecordSource(Protocol):
    """Protocol for record sources."""

    def iter_records(self) -> Iterable[pd.DataFrame]:
        """Return iterable over raw record DataFrame chunks."""


class InMemoryRecordSource(RecordSource):
    """Simple record source backed by an in-memory list."""

    def __init__(self, records: list[RawRecord], chunk_size: int | None = None):
        self._records = list(records)
        self._chunk_size = chunk_size

    def iter_records(self) -> Iterable[pd.DataFrame]:
        df = pd.DataFrame(self._records)
        yield from _chunk_dataframe(df, self._chunk_size)


class ApiRecordSource(RecordSource):
    """Record source that fetches data from an extraction service."""

    def __init__(
        self,
        extraction_service: ExtractionServiceABC,
        entity: str,
        filters: dict[str, Any] | None = None,
        chunk_size: int | None = None,
    ) -> None:
        self._extraction_service = extraction_service
        self._entity = entity
        self._filters = filters or {}
        self._chunk_size = chunk_size

    def iter_records(self) -> Iterable[pd.DataFrame]:
        df = self._extraction_service.extract_all(self._entity, **self._filters)
        yield from _chunk_dataframe(df, self._chunk_size)


def _chunk_dataframe(df: pd.DataFrame, chunk_size: int | None) -> Iterator[pd.DataFrame]:
    if chunk_size is None or chunk_size <= 0:
        yield df
        return

    for start in range(0, len(df), chunk_size):
        yield df.iloc[start : start + chunk_size].reset_index(drop=True)
