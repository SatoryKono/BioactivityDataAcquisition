"""Filtered Data Source wrapper.

Decorates a DataSourcePort with input filtering capability.
Loads filter IDs from external sources (CSV) and passes them to the adapter.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self

from bioetl.domain.ports import FilterableDataSourcePort

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Mapping

    from bioetl.domain.filtering import FilterLoadResult, InputFilterConfig
    from bioetl.domain.ports import DataSourcePort, InputFilterPort, MetricsPort
    from bioetl.domain.types import HealthStatus


class FilteredDataSource:
    """Wraps a DataSourcePort to add CSV-based filtering.

    This is a Decorator pattern implementation that adds filtering
    capability to any DataSourcePort without modifying the original.

    The wrapper:
    1. Loads filter IDs from CSV on context entry
    2. Calls fetch_filtered() on adapters that support it (e.g., ChemblAdapter)
    3. Delegates all other operations to the wrapped adapter
    4. Records metrics about loaded IDs and duplicates

    Multi-column filtering (AND logic):
    When multiple columns are specified, the wrapper uses Hybrid Filtering:
    - Server-side: API request with multiple __in filters (coarse filter)
    - Client-side: Filter results to match only exact row-wise combinations

    Note:
        Filtering requires the underlying adapter to implement FilterableDataSourcePort.
        This Protocol defines the fetch_filtered() method for adapters that support
        server-side filtering (e.g., ChemblAdapter, PubMedAdapter).

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
        metrics: MetricsPort | None = None,
        pipeline_name: str = "unknown",
    ) -> None:
        """Initialize filtered data source wrapper.

        Args:
            data_source: The underlying data source adapter to wrap.
            filter_reader: Reader for loading filter IDs (e.g., CsvFilterReader).
            filter_config: Configuration for filtering behavior.
            metrics: Optional metrics port for recording filter statistics.
            pipeline_name: Pipeline name for metrics labels.

        """
        self._data_source = data_source
        self._filter_reader = filter_reader
        self._filter_config = filter_config
        self._metrics = metrics
        self._pipeline_name = pipeline_name
        self._filter_ids: list[str] | None = None
        self._filter_result: FilterLoadResult | None = None
        # Multi-column filtering state
        self._multi_filter_ids: Mapping[str, list[str]] | None = None
        self._valid_combinations: frozenset[tuple[str, ...]] | None = None
        self._filter_fields: tuple[str, ...] | None = None

    @property
    def provider_name(self) -> str:
        """Provider name from the wrapped data source."""
        return self._data_source.provider_name

    @property
    def filter_result(self) -> FilterLoadResult | None:
        """Access to filter load result with duplicate statistics."""
        return self._filter_result

    async def __aenter__(self) -> Self:
        """Enter async context and load filter IDs if enabled."""
        await self._data_source.__aenter__()

        # Pre-load filter IDs from CSV
        if self._filter_config.enabled and self._filter_reader:
            source_path = self._filter_config.source_path
            if not source_path:
                return self

            # Check if multi-column mode
            columns = self._filter_config.get_columns()
            if len(columns) > 1:
                # Multi-column mode: load all columns
                self._filter_result = (
                    await self._filter_reader.load_multi_column_filter(
                        source_path=source_path,
                        columns=list(columns),
                    )
                )
                # Convert to mutable dict for API calls
                self._multi_filter_ids = {
                    field: list(ids)
                    for field, ids in self._filter_result.column_ids.items()
                }
                self._valid_combinations = self._filter_result.valid_combinations
                self._filter_fields = self._filter_result.filter_fields

                # Record metrics
                self._record_multi_filter_metrics()
            elif self._filter_config.column_name:
                # Single-column mode (backward compatibility)
                self._filter_result = await self._filter_reader.load_filter_ids(
                    source_path=source_path,
                    column_name=self._filter_config.column_name,
                )
                self._filter_ids = list(self._filter_result.ids)

                # Record metrics
                self._record_filter_metrics()

        return self

    def _record_filter_metrics(self) -> None:
        """Record filter loading metrics."""
        if not self._metrics or not self._filter_result:
            return

        source_file = self._filter_config.source_path or "unknown"

        # Record unique IDs loaded
        self._metrics.increment_counter(
            "filter_ids_loaded_total",
            self._filter_result.unique_count,
            {"pipeline": self._pipeline_name, "source_file": source_file},
        )

        # Record duplicates if any
        if self._filter_result.has_duplicates:
            self._metrics.increment_counter(
                "filter_ids_duplicates_total",
                self._filter_result.duplicate_count,
                {"pipeline": self._pipeline_name, "source_file": source_file},
            )

    def _record_multi_filter_metrics(self) -> None:
        """Record multi-column filter loading metrics."""
        if not self._metrics or not self._filter_result:
            return

        source_file = self._filter_config.source_path or "unknown"

        # Record total valid combinations
        if self._valid_combinations:
            self._metrics.increment_counter(
                "filter_combinations_loaded_total",
                len(self._valid_combinations),
                {"pipeline": self._pipeline_name, "source_file": source_file},
            )

        # Record unique IDs per field
        for field, ids in self._filter_result.column_ids.items():
            self._metrics.increment_counter(
                "filter_ids_loaded_total",
                len(ids),
                {
                    "pipeline": self._pipeline_name,
                    "source_file": source_file,
                    "filter_field": field,
                },
            )

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit async context."""
        await self._data_source.__aexit__(exc_type, exc_val, exc_tb)

    def _matches_valid_combination(self, record: dict[str, Any]) -> bool:
        """Check if record matches one of the valid combinations.

        Used for client-side filtering in multi-column mode to ensure
        only exact row-wise combinations from CSV are returned.

        Args:
            record: The record to check.

        Returns:
            True if record matches a valid combination, False otherwise.
        """
        if not self._valid_combinations or not self._filter_fields:
            return True

        # Build tuple of values from record in the same order as filter_fields
        record_values = tuple(
            str(record.get(field, "")) for field in self._filter_fields
        )
        return record_values in self._valid_combinations

    def _ensure_filterable_adapter(self, mode: str) -> None:
        """Check that adapter implements FilterableDataSourcePort."""
        if not isinstance(self._data_source, FilterableDataSourcePort):
            raise TypeError(
                f"Adapter {self._data_source.provider_name} does not implement "
                f"FilterableDataSourcePort. {mode} requires an adapter with "
                "fetch_filtered() method."
            )

    async def _fetch_multi_column(
        self, entity_type: str, limit: int | None
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch with multi-column filtering (hybrid approach)."""
        self._ensure_filterable_adapter("Multi-column filtering")
        fetched_count = 0
        async for record in self._data_source.fetch_multi_filtered(
            entity_type=entity_type,
            filters=dict(self._multi_filter_ids),  # type: ignore[arg-type]
            limit=None,  # Don't limit server-side, we filter client-side
        ):
            if self._matches_valid_combination(record):
                yield record
                fetched_count += 1
                if limit and fetched_count >= limit:
                    return

    async def _fetch_single_column(
        self, entity_type: str, limit: int | None
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch with single-column filtering."""
        self._ensure_filterable_adapter("Filtering")
        config_filter_field = self._filter_config.filter_field
        if config_filter_field is None:
            raise ValueError(
                "filter_field must be specified in InputFilterConfig "
                "when filtering is enabled."
            )
        async for record in self._data_source.fetch_filtered(
            entity_type=entity_type,
            filter_ids=self._filter_ids,  # type: ignore[arg-type]
            filter_field=config_filter_field,
            limit=limit,
        ):
            yield record

    async def fetch(
        self,
        entity_type: str,
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
            limit: Maximum number of records.
            query: Optional search query for providers that support it.
            filter_ids: External filter IDs (ignored - uses internal filter from CSV).
            filter_field: External filter field (ignored - uses internal config).

        Yields:
            Records from the data source, filtered if configured.

        """
        # Note: External filter_ids/filter_field are ignored
        _ = filter_ids, filter_field  # Mark as intentionally unused

        if self._filter_config.enabled and self._multi_filter_ids:
            async for record in self._fetch_multi_column(entity_type, limit):
                yield record
        elif self._filter_config.enabled and self._filter_ids:
            async for record in self._fetch_single_column(entity_type, limit):
                yield record
        else:
            async for record in self._data_source.fetch(
                entity_type=entity_type, limit=limit, query=query
            ):
                yield record

    async def health_check(self) -> HealthStatus:
        """Delegate health check to wrapped adapter."""
        return await self._data_source.health_check()

    async def aclose(self) -> None:
        """Delegate close to wrapped adapter."""
        await self._data_source.aclose()
