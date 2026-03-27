"""Shared mixins for FilteredDataSource behavior."""

from __future__ import annotations

from typing import TYPE_CHECKING, Self, cast

from bioetl.application.core import _filtered_data_source_support as support
from bioetl.application.core._data_source_mixins import (
    _yield_plain_wrapped_fetch_records,
)
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

    async def __aenter__(self) -> Self:
        """Enter async context and preload filters when enabled."""
        await self._data_source.__aenter__()

        if not self._filter_config.enabled:
            return self

        if self._filter_config.direct_multi_filter_ids:
            support.load_direct_multi_filter_ids(self)
            return self

        if self._filter_config.direct_filter_ids:
            support.load_direct_filter_ids(self)
            return self

        await support.load_csv_filter_ids(self)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit async context."""
        await self._data_source.__aexit__(exc_type, exc_val, exc_tb)


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

    def _fetch_without_internal_filters(
        self,
        entity_type: str,
        limit: int | None,
        query: str | None,
        offset: int | None,
    ) -> AsyncIterator[
        JsonDict  # Any: filter record values vary (str|int|float|list)
    ]:  # Any: filter record values vary (str|int|float|list)
        """Delegate plain unfiltered fetches to the wrapped adapter."""
        return _yield_plain_wrapped_fetch_records(
            self._data_source,
            entity_type=entity_type,
            limit=limit,
            query=query,
            offset=offset,
        )

    def fetch(
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
            return self._fetch_multi_column(entity_type, limit)

        if self._filter_config.enabled and self._filter_ids:
            return self._fetch_single_column(entity_type, limit)

        return self._fetch_without_internal_filters(
            entity_type,
            limit,
            query,
            offset,
        )

    async def health_check(self) -> HealthStatus:
        """Delegate health check to wrapped adapter."""
        return await self._data_source.health_check()

    async def aclose(self) -> None:
        """Delegate close to wrapped adapter."""
        await self._data_source.aclose()
