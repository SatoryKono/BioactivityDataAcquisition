"""Filtered Data Source wrapper.

Decorates a DataSourcePort with input filtering capability.
Loads filter IDs from external sources (CSV) and passes them to the adapter.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from bioetl.domain.filter_config import InputFilterConfig
    from bioetl.domain.ports import DataSourcePort, InputFilterPort
    from bioetl.domain.types import HealthStatus, Watermark


class FilteredDataSource:
    """Wraps a DataSourcePort to add CSV-based filtering.

    This is a Decorator pattern implementation that adds filtering
    capability to any DataSourcePort without modifying the original.

    The wrapper:
    1. Loads filter IDs from CSV on context entry
    2. Calls fetch_filtered() on adapters that support it (e.g., ChemblAdapter)
    3. Delegates all other operations to the wrapped adapter

    Note:
        Filtering requires the underlying adapter to implement a fetch_filtered()
        method. This is a provider-specific extension not part of DataSourcePort.

    Example:
        >>> config = InputFilterConfig(
        ...     enabled=True,
        ...     source_path="data/input/molecules.csv",
        ...     column_name="molecule_chembl_id",
        ...     filter_field="molecule_chembl_id",
        ... )
        >>> wrapped = FilteredDataSource(adapter, csv_reader, config)
        >>> async with wrapped:
        ...     async for record in wrapped.fetch("activity"):
        ...         process(record)
    """

    def __init__(
        self,
        data_source: DataSourcePort,
        filter_reader: InputFilterPort | None,
        filter_config: InputFilterConfig,
    ) -> None:
        """Initialize filtered data source wrapper.

        Args:
            data_source: The underlying data source adapter to wrap.
            filter_reader: Reader for loading filter IDs (e.g., CsvFilterReader).
            filter_config: Configuration for filtering behavior.
        """
        self._data_source = data_source
        self._filter_reader = filter_reader
        self._filter_config = filter_config
        self._filter_ids: list[str] | None = None

    @property
    def provider_name(self) -> str:
        """Provider name from the wrapped data source."""
        return self._data_source.provider_name

    async def __aenter__(self) -> Self:
        """Enter async context and load filter IDs if enabled."""
        await self._data_source.__aenter__()

        # Pre-load filter IDs from CSV
        if (
            self._filter_config.enabled
            and self._filter_reader
            and self._filter_config.source_path
            and self._filter_config.column_name
        ):
            self._filter_ids = await self._filter_reader.load_filter_ids(
                source_path=self._filter_config.source_path,
                column_name=self._filter_config.column_name,
            )

        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit async context."""
        await self._data_source.__aexit__(exc_type, exc_val, exc_tb)

    async def fetch(
        self,
        entity_type: str,
        watermark: Watermark | None = None,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch records with optional filtering.

        If filtering is enabled and filter IDs are loaded, uses the adapter's
        fetch_filtered() method if available. Otherwise, delegates to standard fetch().

        Args:
            entity_type: Type of entity to fetch.
            watermark: Last checkpoint for incremental load.
            limit: Maximum number of records.
            query: Optional search query for providers that support it.
            filter_ids: External filter IDs (ignored - uses internal filter from CSV).
            filter_field: External filter field (ignored - uses internal config).

        Yields:
            Records from the data source, filtered if configured.

        Raises:
            TypeError: If filtering is enabled but the adapter doesn't support
                fetch_filtered() method.
        """
        # Note: External filter_ids/filter_field are ignored -
        # this class manages its own filter state from InputFilterConfig
        _ = filter_ids, filter_field  # Mark as intentionally unused
        if self._filter_config.enabled and self._filter_ids:
            # Check if adapter supports filtering (ChEMBL-specific extension)
            if not hasattr(self._data_source, "fetch_filtered"):
                raise TypeError(
                    f"Adapter {self._data_source.provider_name} does not support "
                    "fetch_filtered(). Filtering requires an adapter with this method."
                )
            # Filtered fetch using adapter-specific method
            async for record in self._data_source.fetch_filtered(
                entity_type=entity_type,
                filter_ids=self._filter_ids,
                filter_field=self._filter_config.filter_field,
                watermark=watermark,
                limit=limit,
            ):
                yield record
        else:
            # Standard fetch: no filtering
            async for record in self._data_source.fetch(
                entity_type=entity_type,
                watermark=watermark,
                limit=limit,
                query=query,
            ):
                yield record

    async def health_check(self) -> HealthStatus:
        """Delegate health check to wrapped adapter."""
        return await self._data_source.health_check()

    async def aclose(self) -> None:
        """Delegate close to wrapped adapter."""
        await self._data_source.aclose()
