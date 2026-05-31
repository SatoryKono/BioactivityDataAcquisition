"""Shared mixins for FilteredDataSource behavior."""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from bioetl.application.core import (
    _filtered_data_source_fetch_support as fetch_support,
)
from bioetl.application.core import _filtered_data_source_support as lifecycle_support
from bioetl.application.core._data_source_mixins import (
    _WrappedAdapterHealthDelegationMixin,
)
from bioetl.application.core._fetch_forwarding import delegate_bound_fetch_records
from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from types import TracebackType

    from bioetl.application.core._filtered_data_source_support import (
        _FilteredDataSourceState as _FilteredDataSourceStateBase,
    )
else:

    class _FilteredDataSourceStateBase:
        """Runtime placeholder for the type-checking-only state protocol."""


class _FilteredDataSourceStateMixin(_FilteredDataSourceStateBase):
    """Attribute contract shared by FilteredDataSource mixins."""

    def _ensure_filterable_adapter(self, mode: str) -> None:
        """Check adapter supports filtering mode."""
        raise NotImplementedError


class _FilteredDataSourceLifecycleMixin(_FilteredDataSourceStateMixin):
    """Lifecycle and filter-loading behavior for FilteredDataSource."""

    async def __aenter__(self) -> Self:
        """Enter async context and preload filters when enabled."""
        await lifecycle_support.enter_filtered_data_source(self)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit async context."""
        await self._data_source.__aexit__(exc_type, exc_val, exc_tb)


class _FilteredDataSourceFetchMixin(
    _FilteredDataSourceStateMixin,
    _WrappedAdapterHealthDelegationMixin,
):
    """Fetch and filtering behavior for FilteredDataSource."""

    def _matches_valid_combination(
        self,
        record: JsonDict,  # Any: filter record values vary (str|int|float|list)
    ) -> bool:  # Any: filter record values vary (str|int|float|list)
        """Check if record matches one of the valid combinations."""
        return fetch_support.matches_valid_combination(self, record)

    async def _fetch_multi_column(
        self,
        entity_type: str,
        limit: int | None,
    ) -> AsyncIterator[
        JsonDict  # Any: filter record values vary (str|int|float|list)
    ]:  # Any: filter record values vary (str|int|float|list)
        """Fetch with multi-column filtering (hybrid approach)."""
        async for record in fetch_support.fetch_multi_column(self, entity_type, limit):
            yield record

    async def _fetch_single_column(
        self,
        entity_type: str,
        limit: int | None,
    ) -> AsyncIterator[
        JsonDict  # Any: filter record values vary (str|int|float|list)
    ]:  # Any: filter record values vary (str|int|float|list)
        """Fetch with single-column filtering."""
        async for record in fetch_support.fetch_single_column(self, entity_type, limit):
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
        return fetch_support.fetch_without_internal_filters(
            self,
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
        return delegate_bound_fetch_records(
            fetch_support.fetch_records,
            self,
            entity_type=entity_type,
            limit=limit,
            query=query,
            filter_ids=filter_ids,
            filter_field=filter_field,
            offset=offset,
        )
