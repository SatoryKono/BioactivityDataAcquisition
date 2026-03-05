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


from datetime import UTC, datetime
from pathlib import Path
from types import TracebackType
from typing import TYPE_CHECKING, Self

from bioetl.domain.exceptions import CachedBronzeEmptyError
from bioetl.domain.ports import LoggerPort
from bioetl.domain.types import HealthStatus, JsonDict

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
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit async context manager (no-op for file-based source)."""

    async def health_check(self) -> HealthStatus:
        """Check health of the cached Bronze data source.

        Always returns HEALTHY since this is a local file-based source.

        Returns:
            The HealthStatus result.
        """
        return HealthStatus.HEALTHY

    async def aclose(self) -> None:
        """Close the data source (no-op for file-based source)."""

    def _parse_date(self, date_str: str | None) -> datetime | None:
        """Parse date string to datetime for list_batches filtering."""
        if date_str is None:
            return None
        return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=UTC)

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
        # Note: BronzeWriter with flat_structure=True expects provider/entity
        # to already be in base_path, so we pass empty strings for those.
        # The list_batches method constructs: base_path / provider / entity / date
        # When flat_structure=True and base_path already includes provider/entity,
        # we need to handle this differently.

        # Check if reader has flat_structure enabled
        flat_structure = getattr(self._reader, "_flat_structure", False)

        if flat_structure:
            # flat_structure=True: base_path already has provider/entity
            # list_batches needs empty provider/entity to avoid duplication
            batches = await self._reader.list_batches(
                provider="",
                entity="",
                date=self._parse_date(self._bronze_date),
            )
        else:
            # flat_structure=False: standard path construction
            batches = await self._reader.list_batches(
                provider=self._provider,
                entity=self._entity_type,
                date=self._parse_date(self._bronze_date),
            )

        # Sort for deterministic ordering (ADR-014)
        return sorted(batches)

    async def fetch(
        self,
        entity_type: str,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
        offset: int | None = None,
    ) -> AsyncIterator[JsonDict]:  # Any: untyped API JSON record
        """Fetch records from cached Bronze files."""
        _ = entity_type, filter_field, offset
        self._log_unsupported_fetch_params(query=query, filter_ids=filter_ids)
        batches = await self._list_batches_sorted()
        self._logger.info(
            "cached_bronze_fetch_start",
            batch_count=len(batches),
            date_filter=self._bronze_date,
            limit=limit,
        )
        self._raise_if_empty_batches(batches)

        count = 0
        async for record in self._iter_batch_records(batches):
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

    def _log_unsupported_fetch_params(
        self,
        *,
        query: str | None,
        filter_ids: list[str] | None,
    ) -> None:
        """Log ignored fetch parameters for cached Bronze source."""
        if query:
            self._logger.warning(
                "cached_bronze_query_ignored",
                query=query,
                reason="query parameter not supported for cached Bronze",
            )
        if filter_ids:
            self._logger.warning(
                "cached_bronze_filter_ignored",
                filter_count=len(filter_ids),
                reason="filter_ids not supported for cached Bronze",
            )

    def _resolve_bronze_path(self) -> str:
        """Resolve effective Bronze path for empty-cache errors."""
        bronze_path = str(self._reader.base_path)
        if getattr(self._reader, "_flat_structure", False):
            return bronze_path
        return str(Path(bronze_path) / self._provider / self._entity_type)

    def _raise_if_empty_batches(self, batches: list[str]) -> None:
        """Raise domain error when no cached Bronze batches are available."""
        if batches:
            return
        raise CachedBronzeEmptyError(
            provider=self._provider,
            entity_type=self._entity_type,
            bronze_path=self._resolve_bronze_path(),
            date_filter=self._bronze_date,
        )

    async def _iter_batch_records(
        self,
        batches: list[str],
    ) -> AsyncIterator[JsonDict]:  # Any: untyped API JSON record
        """Iterate records from sorted batch paths."""
        for batch_path in batches:
            self._logger.debug("cached_bronze_reading_batch", batch_path=batch_path)
            async for record in self._reader.read_bronze(batch_path):
                yield record

    async def get_total_records(self) -> int:
        """Get total number of records across all cached batches.

        This is used for progress reporting. It performs a quick pass over
        the files to count records without full JSON parsing where possible.

        Returns:
            Total records.
        """
        batches = await self._list_batches_sorted()
        total = 0

        self._logger.info(
            "Estimating total records in Bronze cache...", batch_count=len(batches)
        )

        for batch_path in batches:
            # We use a simpler counting method if available, or just use the reader
            async for _ in self._reader.read_bronze(batch_path):
                total += 1

        self._logger.info("Total records estimated", total=total)
        return total
