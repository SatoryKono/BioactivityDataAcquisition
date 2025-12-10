"""Core record source interfaces and helpers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Any, Callable

from pydantic import BaseModel, ConfigDict

from bioetl.domain.ports.extraction import RecordFetcherABC


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


class ApiRecordSource(RecordSourceABC):
    """Record source that fetches data from an extraction service."""

    def __init__(
        self,
        extraction_service: RecordFetcherABC,
        entity: str,
        filters: dict[str, Any] | None = None,
        chunk_size: int | None = None,
        batch_adapter: Callable[[Any], list[RawRecord]] | None = None,
    ) -> None:
        self._extraction_service = extraction_service
        self._entity = entity
        self._filters = filters or {}
        self._chunk_size = chunk_size
        self._batch_adapter = batch_adapter

    def iter_records(self) -> Iterable[list[RawRecord]]:
        """Iterate over extracted provider batches as normalized records."""
        filters = dict(self._filters)
        for raw_batch in self._extraction_service.iter_extract(
            self._entity, chunk_size=self._chunk_size, **filters
        ):
            if self._batch_adapter is not None:
                yield self._batch_adapter(raw_batch)
                continue

            if not isinstance(raw_batch, list):
                raise TypeError(
                    "iter_extract must yield list[RawRecord] when no batch_adapter "
                    "is set."
                )

            yield raw_batch
