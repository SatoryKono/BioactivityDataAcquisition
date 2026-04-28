"""Derived-target mixins and helpers for application data source wrappers."""

from __future__ import annotations

from bioetl.application.core._fetch_forwarding import forward_fetch_records

__all__ = [
    "_FallbackFilterableTargetFetchMixin",
    "_FilterableTargetDelegationMixin",
    "_TargetEntityFetchDelegationMixin",
    "_yield_plain_wrapped_fetch_records",
    "_yield_wrapped_fetch_records",
]

from typing import TYPE_CHECKING, Protocol, TypeVar, cast

from bioetl.application.core._target_data_source_fetch_support import (
    ensure_filterable_data_source,
    yield_target_or_delegate_records,
    yield_target_records_from_fallback_fetch,
)
from bioetl.application.core._target_data_source_fetch_support import (
    yield_plain_wrapped_fetch_records as _yield_plain_wrapped_fetch_records,
)
from bioetl.application.core._target_data_source_fetch_support import (
    yield_wrapped_fetch_records as _yield_wrapped_fetch_records,
)
from bioetl.domain.ports import FilterableDataSourcePort

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from bioetl.domain.ports import DataSourcePort

RecordT = TypeVar("RecordT")
RecordOutT = TypeVar("RecordOutT", covariant=True)


class _TargetEntityFetchWrapper(Protocol[RecordOutT]):
    _data_source: DataSourcePort
    TARGET_ENTITY_TYPE: str

    def _fetch_target_records(
        self,
        limit: int | None,
        query: str | None,
        filter_ids: list[str] | None,
        filter_field: str | None,
        offset: int | None,
    ) -> AsyncIterator[RecordOutT]: ...


class _TargetEntityFetchDelegationMixin:
    def fetch(
        self: _TargetEntityFetchWrapper[RecordT],
        entity_type: str,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
        offset: int | None = None,
    ) -> AsyncIterator[RecordT]:
        """Fetch derived target records or delegate to the wrapped adapter."""
        if entity_type == self.TARGET_ENTITY_TYPE:
            return self._fetch_target_records(
                limit,
                query,
                filter_ids,
                filter_field,
                offset,
            )

        return _yield_wrapped_fetch_records(
            self._data_source,
            entity_type=entity_type,
            limit=limit,
            query=query,
            filter_ids=filter_ids,
            filter_field=filter_field,
            offset=offset,
        )


class _FilterableTargetWrapper(Protocol[RecordOutT]):
    _data_source: DataSourcePort
    SOURCE_ENTITY_TYPE: str
    TARGET_ENTITY_TYPE: str

    def _fetch_target_filtered_records(
        self,
        filterable: FilterableDataSourcePort,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None,
    ) -> AsyncIterator[RecordOutT]: ...

    def _fetch_target_multi_filtered_records(
        self,
        filterable: FilterableDataSourcePort,
        filters: dict[str, list[str]],
        limit: int | None,
    ) -> AsyncIterator[RecordOutT]: ...

    def _fetch_target_filtered_with_fallback_records(
        self,
        filterable: FilterableDataSourcePort,
        filter_ids: list[str],
        filter_field: str,
        fallback_mapping: dict[str, str],
        limit: int | None,
    ) -> AsyncIterator[RecordOutT]: ...


class _FilterableTargetDelegatingWrapper(
    _FilterableTargetWrapper[RecordOutT],
    Protocol[RecordOutT],
):
    def _ensure_filterable(self, method_name: str) -> FilterableDataSourcePort: ...


class _FallbackFilterableTargetWrapper(Protocol[RecordOutT]):
    SOURCE_ENTITY_TYPE: str

    def _resolve_target_fallback_upstream_limit(
        self,
        limit: int | None,
    ) -> int | None: ...

    def _yield_target_records_from_fallback_source_records(
        self,
        source_records: AsyncIterator[object],
        limit: int | None,
    ) -> AsyncIterator[RecordOutT]: ...


class _FilterableTargetDelegationMixin:
    def _ensure_filterable(
        self: _FilterableTargetWrapper[RecordT],
        method_name: str,
    ) -> FilterableDataSourcePort:
        """Validate wrapped source implements FilterableDataSourcePort."""
        return ensure_filterable_data_source(
            self._data_source,
            provider_name=self._data_source.provider_name,
            method_name=method_name,
        )

    async def fetch_filtered(
        self: _FilterableTargetDelegatingWrapper[RecordT],
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None = None,
    ) -> AsyncIterator[RecordT]:
        """Fetch filtered records, deriving target records when requested."""
        filterable = self._ensure_filterable("fetch_filtered")
        async for record in yield_target_or_delegate_records(
            entity_type=entity_type,
            target_entity_type=self.TARGET_ENTITY_TYPE,
            target_factory=lambda: self._fetch_target_filtered_records(
                filterable, filter_ids, filter_field, limit
            ),
            delegate_factory=lambda: filterable.fetch_filtered(
                entity_type=entity_type,
                filter_ids=filter_ids,
                filter_field=filter_field,
                limit=limit,
            ),
        ):
            yield cast("RecordT", record)

    async def fetch_multi_filtered(
        self: _FilterableTargetDelegatingWrapper[RecordT],
        entity_type: str,
        filters: dict[str, list[str]],
        limit: int | None = None,
    ) -> AsyncIterator[RecordT]:
        """Fetch multi-filtered records, deriving target records when requested."""
        filterable = self._ensure_filterable("fetch_multi_filtered")
        async for record in yield_target_or_delegate_records(
            entity_type=entity_type,
            target_entity_type=self.TARGET_ENTITY_TYPE,
            target_factory=lambda: self._fetch_target_multi_filtered_records(
                filterable, filters, limit
            ),
            delegate_factory=lambda: filterable.fetch_multi_filtered(
                entity_type=entity_type,
                filters=filters,
                limit=limit,
            ),
        ):
            yield cast("RecordT", record)

    async def fetch_filtered_with_fallback(
        self: _FilterableTargetDelegatingWrapper[RecordT],
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        fallback_mapping: dict[str, str],
        limit: int | None = None,
    ) -> AsyncIterator[RecordT]:
        """Fetch fallback-enabled records, deriving target records when requested."""
        filterable = self._ensure_filterable("fetch_filtered_with_fallback")
        async for record in yield_target_or_delegate_records(
            entity_type=entity_type,
            target_entity_type=self.TARGET_ENTITY_TYPE,
            target_factory=lambda: self._fetch_target_filtered_with_fallback_records(
                filterable,
                filter_ids,
                filter_field,
                fallback_mapping,
                limit,
            ),
            delegate_factory=lambda: filterable.fetch_filtered_with_fallback(
                entity_type=entity_type,
                filter_ids=filter_ids,
                filter_field=filter_field,
                fallback_mapping=fallback_mapping,
                limit=limit,
            ),
        ):
            yield cast("RecordT", record)


class _FallbackFilterableTargetFetchMixin:
    def _fetch_target_filtered_with_fallback_records(
        self: _FallbackFilterableTargetWrapper[RecordT],
        filterable: FilterableDataSourcePort,
        filter_ids: list[str],
        filter_field: str,
        fallback_mapping: dict[str, str],
        limit: int | None,
    ) -> AsyncIterator[RecordT]:
        """Yield target records from fallback-enabled upstream records."""
        return yield_target_records_from_fallback_fetch(
            filterable,
            source_entity_type=self.SOURCE_ENTITY_TYPE,
            filter_ids=filter_ids,
            filter_field=filter_field,
            fallback_mapping=fallback_mapping,
            upstream_limit=self._resolve_target_fallback_upstream_limit(limit),
            limit=limit,
            target_yielder=self._yield_target_records_from_fallback_source_records,
        )
