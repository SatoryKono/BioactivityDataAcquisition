"""Filtered Data Source wrapper.

Decorates a DataSourcePort with input filtering capability.
Loads filter IDs from external sources (CSV) and passes them to the adapter.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self

from bioetl.domain.ports import (
    FallbackFilterableDataSourcePort,
    FallbackInputFilterPort,
    FilterableDataSourcePort,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Mapping

    from bioetl.domain.filtering import FilterLoadResult, InputFilterConfig
    from bioetl.domain.ports import DataSourcePort, InputFilterPort, MetricsPort
    from bioetl.domain.types import HealthStatus


class FilteredDataSource:
    """Wraps a DataSourcePort to add CSV-based filtering.

    Decorator pattern: loads filter IDs from CSV, calls fetch_filtered() on
    adapters that support it, delegates all other operations to wrapped adapter.
    Multi-column filtering uses hybrid approach (server + client-side filtering).
    """

    def __init__(
        self,
        data_source: DataSourcePort,
        filter_reader: InputFilterPort | None,
        filter_config: InputFilterConfig,
        metrics: MetricsPort | None = None,
        pipeline_name: str = "unknown",
    ) -> None:
        """Initialize filtered data source wrapper."""
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
        # Fallback mapping state (e.g., DOI → title)
        self._fallback_mapping: dict[str, str] | None = None

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
                # Check if fallback column is configured
                if self._filter_config.fallback_column and isinstance(
                    self._filter_reader, FallbackInputFilterPort
                ):
                    # Load with fallback mapping
                    self._filter_result, self._fallback_mapping = (
                        await self._filter_reader.load_filter_with_fallback(
                            source_path=source_path,
                            primary_column=self._filter_config.column_name,
                            fallback_column=self._filter_config.fallback_column,
                        )
                    )
                else:
                    # Standard loading without fallback
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
        """Check if record matches one of the valid combinations."""
        if not self._valid_combinations or not self._filter_fields:
            return True
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
        assert isinstance(self._data_source, FilterableDataSourcePort)
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
        assert isinstance(self._data_source, FilterableDataSourcePort)
        config_filter_field = self._filter_config.filter_field
        if config_filter_field is None:
            raise ValueError(
                "filter_field must be specified in InputFilterConfig "
                "when filtering is enabled."
            )

        # Check if adapter supports fallback and we have fallback mapping
        if self._fallback_mapping and isinstance(
            self._data_source, FallbackFilterableDataSourcePort
        ):
            async for record in self._data_source.fetch_filtered_with_fallback(
                entity_type=entity_type,
                filter_ids=self._filter_ids,  # type: ignore[arg-type]
                filter_field=config_filter_field,
                fallback_mapping=self._fallback_mapping,
                limit=limit,
            ):
                yield record
        else:
            # Standard path without fallback
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
        """Fetch records with optional filtering from internal CSV config."""
        _ = filter_ids, filter_field  # External params ignored, use internal config

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
