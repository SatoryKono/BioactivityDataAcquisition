"""Core record source interfaces and helpers."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Callable, Protocol, TypedDict, cast

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

            yield cast(list[RawRecord], raw_batch)
