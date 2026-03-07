"""Shared mixins for FilteredDataSource behavior."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self, cast

from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Mapping
    from types import TracebackType

    from bioetl.domain.filtering import FilterLoadResult, InputFilterConfig
    from bioetl.domain.ports import (
        DataSourcePort,
        FilterableDataSourcePort,
        InputFilterPort,
        LoggerPort,
        MetricsPort,
    )
    from bioetl.domain.types import HealthStatus


class _FilteredDataSourceStateMixin:
    """Attribute contract shared by FilteredDataSource mixins."""

    _data_source: DataSourcePort
    _filter_reader: InputFilterPort | None
    _filter_config: InputFilterConfig
    _metrics: MetricsPort | None
    _pipeline_name: str
    _logger: LoggerPort | None
    _filter_ids: list[str] | None
    _filter_result: FilterLoadResult | None
    _multi_filter_ids: Mapping[str, list[str]] | None
    _valid_combinations: frozenset[tuple[str, ...]] | None
    _filter_fields: tuple[str, ...] | None
    _fallback_mapping: dict[str, str] | None

    def _ensure_filterable_adapter(self, mode: str) -> None:
        """Check adapter supports filtering mode."""
        raise NotImplementedError


class _FilteredDataSourceLifecycleMixin(_FilteredDataSourceStateMixin):
    """Lifecycle and filter-loading behavior for FilteredDataSource."""

    def _log_filter_file_not_found(self, source_path: str) -> None:
        """Log warning when filter file is not found."""
        if self._logger:
            self._logger.warning(
                "input_filter_file_not_found",
                source_path=source_path,
                pipeline=self._pipeline_name,
                message="Filter file not found, proceeding without filtering",
            )

    async def __aenter__(self) -> Self:
        """Enter async context and preload filters when enabled."""
        await self._data_source.__aenter__()

        if not self._filter_config.enabled:
            return self

        if self._filter_config.direct_multi_filter_ids:
            self._load_direct_multi_filter_ids()
            return self

        if self._filter_config.direct_filter_ids:
            self._load_direct_filter_ids()
            return self

        await self._load_csv_filter_ids()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit async context."""
        await self._data_source.__aexit__(exc_type, exc_val, exc_tb)

    def _load_direct_multi_filter_ids(self) -> None:
        """Load direct multi-field filter IDs from configuration."""
        multi_ids = self._filter_config.direct_multi_filter_ids or {}
        self._multi_filter_ids = {field: list(ids) for field, ids in multi_ids.items()}
        filter_fields = tuple(multi_ids.keys())
        self._filter_fields = filter_fields
        self._valid_combinations = self._filter_config.direct_valid_combinations
        if self._logger:
            self._logger.info(
                "direct_multi_filter_ids_loaded",
                fields=list(filter_fields),
                counts={f: len(ids) for f, ids in multi_ids.items()},
                valid_combinations_count=len(self._valid_combinations)
                if self._valid_combinations
                else 0,
                pipeline=self._pipeline_name,
            )

    def _load_direct_filter_ids(self) -> None:
        """Load direct filter IDs from configuration."""
        loaded_filter_ids = list(self._filter_config.direct_filter_ids or [])
        self._filter_ids = loaded_filter_ids
        self._fallback_mapping = self._filter_config.direct_fallback_mapping
        if self._logger:
            self._logger.info(
                "direct_filter_ids_loaded",
                count=len(loaded_filter_ids),
                fallback_mapping_size=len(self._fallback_mapping)
                if self._fallback_mapping
                else 0,
                filter_field=self._filter_config.filter_field,
                pipeline=self._pipeline_name,
            )

    async def _load_csv_filter_ids(self) -> None:
        """Load filter IDs from CSV file."""
        if not self._filter_reader:
            return

        source_path = self._filter_config.source_path
        if not source_path:
            return

        columns = self._filter_config.get_columns()
        try:
            if len(columns) > 1:
                await self._load_multi_column_filter(source_path, columns)
            elif self._filter_config.column_name:
                await self._load_single_column_filter(source_path)
        except FileNotFoundError:
            self._log_filter_file_not_found(source_path)

    async def _load_multi_column_filter(
        self,
        source_path: str,
        columns: tuple[Any, ...],  # Any: tuple element types vary
    ) -> None:
        """Load multi-column filter from CSV."""
        assert self._filter_reader is not None
        result = await self._filter_reader.load_multi_column_filter(
            source_path=source_path,
            columns=list(columns),
        )
        self._filter_result = result
        self._multi_filter_ids = {
            field: list(ids) for field, ids in result.column_ids.items()
        }
        self._valid_combinations = result.valid_combinations
        self._filter_fields = result.filter_fields
        self._record_multi_filter_metrics()

    async def _load_single_column_filter(self, source_path: str) -> None:
        """Load single-column filter from CSV."""
        assert self._filter_reader is not None
        assert self._filter_config.column_name is not None
        if self._filter_config.fallback_column:
            (
                self._filter_result,
                self._fallback_mapping,
            ) = await self._filter_reader.load_filter_with_fallback(
                source_path=source_path,
                primary_column=self._filter_config.column_name,
                fallback_column=self._filter_config.fallback_column,
            )
        else:
            self._filter_result = await self._filter_reader.load_filter_ids(
                source_path=source_path,
                column_name=self._filter_config.column_name,
            )
        assert self._filter_result is not None
        self._filter_ids = list(self._filter_result.ids)
        self._record_filter_metrics()

    def _record_filter_metrics(self) -> None:
        """Record single-column filter loading metrics."""
        if not self._metrics or not self._filter_result:
            return

        source_file = self._filter_config.source_path or "unknown"
        self._metrics.increment_counter(
            "filter_ids_loaded_total",
            self._filter_result.unique_count,
            {"pipeline": self._pipeline_name, "source_file": source_file},
        )
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
        if self._valid_combinations:
            self._metrics.increment_counter(
                "filter_combinations_loaded_total",
                len(self._valid_combinations),
                {"pipeline": self._pipeline_name, "source_file": source_file},
            )

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


class _FilteredDataSourceFetchMixin(_FilteredDataSourceStateMixin):
    """Fetch and filtering behavior for FilteredDataSource."""

    def _matches_valid_combination(
        self,
        record: JsonDict,  # Any: filter record values vary (str|int|float|list)
    ) -> bool:  # Any: filter record values vary (str|int|float|list)
        """Check if record matches one of the valid combinations."""
        if not self._valid_combinations or not self._filter_fields:
            return True
        record_values = tuple(
            str(record.get(field, "")) for field in self._filter_fields
        )
        return record_values in self._valid_combinations

    async def _fetch_multi_column(
        self,
        entity_type: str,
        limit: int | None,
    ) -> AsyncIterator[
        JsonDict  # Any: filter record values vary (str|int|float|list)
    ]:  # Any: filter record values vary (str|int|float|list)
        """Fetch with multi-column filtering (hybrid approach)."""
        self._ensure_filterable_adapter("Multi-column filtering")
        adapter = cast("FilterableDataSourcePort", self._data_source)
        assert self._multi_filter_ids is not None
        fetched_count = 0
        async for record in adapter.fetch_multi_filtered(
            entity_type=entity_type,
            filters=dict(self._multi_filter_ids),
            limit=None,
        ):
            if self._matches_valid_combination(record):
                yield record
                fetched_count += 1
                if limit and fetched_count >= limit:
                    return

    async def _fetch_single_column(
        self,
        entity_type: str,
        limit: int | None,
    ) -> AsyncIterator[
        JsonDict  # Any: filter record values vary (str|int|float|list)
    ]:  # Any: filter record values vary (str|int|float|list)
        """Fetch with single-column filtering."""
        self._ensure_filterable_adapter("Filtering")
        adapter = cast("FilterableDataSourcePort", self._data_source)
        config_filter_field = self._filter_config.filter_field
        if config_filter_field is None:
            raise ValueError(
                "filter_field must be specified in InputFilterConfig "
                "when filtering is enabled."
            )
        assert self._filter_ids is not None

        if self._fallback_mapping:
            async for record in adapter.fetch_filtered_with_fallback(
                entity_type=entity_type,
                filter_ids=self._filter_ids,
                filter_field=config_filter_field,
                fallback_mapping=self._fallback_mapping,
                limit=limit,
            ):
                yield record
            return

        async for record in adapter.fetch_filtered(
            entity_type=entity_type,
            filter_ids=self._filter_ids,
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
        offset: int | None = None,
    ) -> AsyncIterator[
        JsonDict  # Any: filter record values vary (str|int|float|list)
    ]:  # Any: filter record values vary (str|int|float|list)
        """Fetch records with optional filtering from internal config.

        Args:
            entity_type: Entity type string passed through to the underlying adapter.
            limit: Maximum number of records to fetch, or None for all.
            query: Optional query string passed through to the adapter.
            filter_ids: Ignored; filtering is driven by internal config filter_ids.
            filter_field: Ignored; filtering is driven by internal config filter_field.
            offset: Optional pagination offset passed through to the adapter.
        """
        _ = filter_ids, filter_field

        if self._filter_config.enabled and self._multi_filter_ids:
            async for record in self._fetch_multi_column(entity_type, limit):
                yield record
            return

        if self._filter_config.enabled and self._filter_ids:
            async for record in self._fetch_single_column(entity_type, limit):
                yield record
            return

        async for record in self._data_source.fetch(
            entity_type=entity_type,
            limit=limit,
            query=query,
            offset=offset,
        ):
            yield record

    async def health_check(self) -> HealthStatus:
        """Delegate health check to wrapped adapter."""
        return await self._data_source.health_check()

    async def aclose(self) -> None:
        """Delegate close to wrapped adapter."""
        await self._data_source.aclose()
