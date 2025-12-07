"""Core record source interfaces and helpers."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any, Protocol, TypedDict, cast

import pandas as pd

from bioetl.domain.contracts import ExtractionServiceABC


class RawRecord(TypedDict, total=False):
    """Raw record type before normalization."""

    # Arbitrary key/value mapping for raw provider payloads
    ...


class RecordSource(Protocol):
    """Protocol for record sources returning record batches."""

    def iter_records(self) -> Iterable[list[RawRecord]]:
        """Return iterable over raw record batches as lists of mappings."""


class InMemoryRecordSource(RecordSource):
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

    def iter_records(self) -> Iterable[list[RawRecord]]:
        """Iterate over extracted provider batches as normalized records."""
        filters = dict(self._filters)
        for raw_batch in self._extraction_service.iter_extract(
            self._entity, chunk_size=self._chunk_size, **filters
        ):
            yield self._coerce_batch(raw_batch)

    def _coerce_batch(self, raw_batch: Any) -> list[RawRecord]:
        """
        Normalize provider batches to a list of raw records.

        Supports DataFrame, mapping, iterable of mappings, and None.
        """
        if raw_batch is None:
            return []

        if isinstance(raw_batch, pd.DataFrame):
            return cast(list[RawRecord], raw_batch.to_dict(orient="records"))

        if isinstance(raw_batch, dict):
            return [cast(RawRecord, raw_batch)]

        if isinstance(raw_batch, list):
            return cast(list[RawRecord], raw_batch)

        if isinstance(raw_batch, Iterable) and not isinstance(raw_batch, (str, bytes)):
            return cast(list[RawRecord], list(raw_batch))

        raise TypeError(
            "iter_extract must yield DataFrame, mapping, or iterable of mappings."
        )


class FileRecordSourceFactoryABC(Protocol):
    """Factory for file-based record sources (CSV and ID list)."""

    def create_csv_source(
        self,
        *,
        input_path: Path,
        csv_options: Any,
        limit: int | None,
        chunk_size: int | None,
        logger: Any,
    ) -> RecordSource:
        """Create CSV-backed record source."""

    def create_id_list_source(
        self,
        *,
        input_path: Path,
        id_column: str,
        csv_options: Any,
        limit: int | None,
        chunk_size: int | None,
        extraction_service: ExtractionServiceABC,
        source_config: Any,
        entity: str,
        filter_key: str,
        logger: Any,
    ) -> RecordSource:
        """Create ID-list-backed record source."""
