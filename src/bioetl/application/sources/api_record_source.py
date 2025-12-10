"""
API-based record source implementation.

This module was moved from bioetl.domain.record_source to application layer
as part of Hexagonal Architecture refactoring. The ApiRecordSource contains
orchestration logic that belongs in the application layer, not the domain layer.

Previous location: bioetl.domain.record_source
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Callable

from bioetl.domain.ports.extraction import RecordFetcherABC
from bioetl.domain.record_source import RawRecord, RecordSourceABC


class ApiRecordSource(RecordSourceABC):
    """Record source that fetches data from an extraction service.

    This class orchestrates data fetching from external APIs via a
    RecordFetcherABC port. It belongs in the application layer as it
    coordinates infrastructure concerns with domain logic.

    Args:
        extraction_service: The extraction service port for fetching records.
        entity: The entity type to fetch (e.g., 'molecule', 'activity').
        filters: Optional filters to apply during extraction.
        chunk_size: Optional batch size for chunked iteration.
        batch_adapter: Optional callable to transform raw batches to RawRecord lists.

    Example:
        >>> source = ApiRecordSource(
        ...     extraction_service=chembl_fetcher,
        ...     entity="molecule",
        ...     filters={"molecule_type": "Small molecule"},
        ...     chunk_size=1000,
        ... )
        >>> for batch in source.iter_records():
        ...     process(batch)
    """

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
        """Iterate over extracted provider batches as normalized records.

        Yields:
            Lists of RawRecord instances, each list representing a batch
            of records from the extraction service.

        Raises:
            TypeError: If iter_extract yields non-list values and no
                batch_adapter is configured.
        """
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
