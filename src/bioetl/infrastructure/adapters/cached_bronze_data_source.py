"""Cached Bronze data source adapter.

Implements DataSourcePort by reading from cached Bronze layer files instead
of making API calls. Used for re-processing without network access or
for testing transformations on previously fetched data.

ADR-014 Compliance:
- Batches are sorted by date then filename for deterministic ordering
- All operations are reproducible across runs

RULES.md §1.2 - Infrastructure Layer:
- Implements domain port (DataSourcePort)
- No domain logic, only I/O operations
"""

from __future__ import annotations

__all__ = ["CachedBronzeDataSource"]

import asyncio
from types import TracebackType
from typing import TYPE_CHECKING, Self

from bioetl.domain.ports import LoggerPort
from bioetl.domain.types import HealthStatus, JsonDict
from bioetl.infrastructure.adapters._cached_bronze_support import (
    count_batch_records,
    iter_batch_records,
    list_sorted_batches,
    log_unsupported_fetch_params,
    raise_if_empty_batches,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from bioetl.infrastructure.storage.bronze_writer import BronzeWriter


class CachedBronzeDataSource:
    """DataSource adapter that reads from cached Bronze layer files.

    Implements DataSourcePort protocol by reading JSONL+zstd files from Bronze
    storage instead of making API calls. Useful for:
    - Re-processing data without API access
    - Testing transformations on previously fetched data
    - Faster iteration during development

    ADR-014 Compliance:
    - Batches are sorted lexicographically for deterministic ordering
    - Path format: {date}/batch_{date}_{uuid}.jsonl.zst

    Attributes:
        provider_name: Provider identifier (e.g., 'chembl').

    Example:
        >>> from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
        >>> writer = BronzeWriter(base_path="/data/bronze/chembl/activity", ...)
        >>> source = CachedBronzeDataSource(
        ...     bronze_reader=writer,
        ...     provider="chembl",
        ...     entity_type="activity",
        ...     logger=logger,
        ... )
        >>> async for record in source.fetch("activity", limit=100):
        ...     process(record)
    """

    def __init__(
        self,
        bronze_reader: BronzeWriter,
        provider: str,
        entity_type: str,
        logger: LoggerPort,
        bronze_date: str | None = None,
    ) -> None:
        """Initialize CachedBronzeDataSource.

        Args:
            bronze_reader: BronzeWriter instance for reading Bronze files.
                Reuses BronzeWriter's read_bronze() and list_batches() methods.
            provider: Provider name (e.g., 'chembl').
            entity_type: Entity type (e.g., 'activity').
            logger: LoggerPort for structured logging.
            bronze_date: Optional date filter in YYYY-MM-DD format.
                When set, only reads batches from that specific date directory.
        """
        self._reader = bronze_reader
        self._provider = provider
        self._entity_type = entity_type
        self._logger = logger.bind(
            adapter="cached_bronze",
            provider=provider,
            entity_type=entity_type,
        )
        self._bronze_date = bronze_date

    @property
    def provider_name(self) -> str:
        """Return the provider name."""
        return self._provider

    async def __aenter__(self) -> Self:
        """Enter async context manager (no-op for file-based source)."""
        await asyncio.sleep(0)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit async context manager (no-op for file-based source)."""
        await asyncio.sleep(0)

    async def health_check(self) -> HealthStatus:
        """Check health of the cached Bronze data source.

        Always returns HEALTHY since this is a local file-based source.

        Returns:
            The HealthStatus result.
        """
        await asyncio.sleep(0)
        return HealthStatus.HEALTHY

    async def aclose(self) -> None:
        """Close the data source (no-op for file-based source)."""
        await asyncio.sleep(0)

    async def _list_batches_sorted(self) -> list[str]:
        """List batches with deterministic sorting (ADR-014).

        Bronze files are stored in date subdirectories:
        - With flat_structure=True: {date}/batch_{date}_{uuid}.jsonl.zst
        - With flat_structure=False: {provider}/{entity}/{date}/batch_...

        Sorting by path ensures:
        1. Earlier dates come first
        2. Within same date, files sorted alphabetically by UUID

        Returns:
            List of relative paths, sorted lexicographically.
        """
        return await list_sorted_batches(
            self._reader,
            provider=self._provider,
            entity_type=self._entity_type,
            bronze_date=self._bronze_date,
        )

    async def fetch(
        self,
        entity_type: str,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
        offset: int | None = None,
    ) -> AsyncIterator[JsonDict]:  # Any: untyped API JSON record
        """Fetch records from cached Bronze files.

        Args:
            entity_type: Entity type identifier (ignored; source is fixed at construction time).
            limit: Optional maximum number of records to yield before stopping.
            query: Optional query string (not supported; logs a warning if provided).
            filter_ids: Optional ID filter list (not supported; logs a warning if provided).
            filter_field: Optional filter field name (ignored for file-based source).
            offset: Optional record offset (ignored for file-based source).

        Yields:
            Bronze records read from cached JSONL+zstd batch files.

        Raises:
            CachedBronzeEmptyError: If no batch files are found in Bronze storage.
        """
        _ = entity_type, filter_field, offset
        log_unsupported_fetch_params(
            self._logger,
            query=query,
            filter_ids=filter_ids,
        )
        batches = await self._list_batches_sorted()
        self._logger.info(
            "cached_bronze_fetch_start",
            batch_count=len(batches),
            date_filter=self._bronze_date,
            limit=limit,
        )
        raise_if_empty_batches(
            batches,
            reader=self._reader,
            provider=self._provider,
            entity_type=self._entity_type,
            bronze_date=self._bronze_date,
        )

        count = 0
        async for record in iter_batch_records(self._reader, self._logger, batches):
            yield record
            count += 1
            if limit is not None and count >= limit:
                self._logger.info(
                    "cached_bronze_fetch_limit_reached",
                    records_yielded=count,
                    limit=limit,
                )
                return
        self._logger.info(
            "cached_bronze_fetch_complete",
            records_yielded=count,
            batches_processed=len(batches),
        )

    async def get_total_records(self) -> int:
        """Get total number of records across all cached batches.

        This is used for progress reporting. It performs a quick pass over
        the files to count records without full JSON parsing where possible.

        Returns:
            Total records.
        """
        batches = await self._list_batches_sorted()
        return await count_batch_records(self._reader, self._logger, batches)
