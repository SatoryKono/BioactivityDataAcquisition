"""Shared mixins for application data source wrappers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, TypeVar

from bioetl.domain.ports import FilterableDataSourcePort

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable

RecordT = TypeVar("RecordT")

class _HasWrappedDataSource(Protocol):
    """Structural protocol for application classes that wrap a data source adapter.

    Used as a self-type constraint in mixin methods that need to access
    the wrapped ``_data_source`` attribute without inheriting from a concrete class.
    Conforms to the Ports and Adapters pattern (Hexagonal Architecture) where the
    application layer delegates to an injected infrastructure adapter.

    Attributes:
        _data_source: The wrapped data source adapter instance.
    """

    _data_source: object


class _SourceMetadataDelegationMixin:
    """Mixin for delegating get_source_metadata to wrapped data source."""

    def get_source_metadata(
        self: _HasWrappedDataSource, api_version: str | None = None
    ) -> Any:  # Any: SourceMetadata type varies per adapter implementation
        """Delegate get_source_metadata to wrapped data source if supported.

        Args:
            api_version: Api version.

        Returns:
            Source metadata.
        """
        get_metadata = getattr(self._data_source, "get_source_metadata", None)
        if get_metadata is not None and callable(get_metadata):
            return get_metadata(api_version)
        return None


class _FilterableTargetWrapper(Protocol):
    """Structural contract for wrappers exposing a derived target entity."""

    _data_source: object
    SOURCE_ENTITY_TYPE: str
    TARGET_ENTITY_TYPE: str

    async def _fetch_target_filtered_records(
        self,
        filterable: FilterableDataSourcePort,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None,
    ) -> AsyncIterator[Any]:
        """Yield target records from a filtered upstream stream."""

    async def _fetch_target_multi_filtered_records(
        self,
        filterable: FilterableDataSourcePort,
        filters: dict[str, list[str]],
        limit: int | None,
    ) -> AsyncIterator[Any]:
        """Yield target records from a multi-filtered upstream stream."""

    async def _fetch_target_filtered_with_fallback_records(
        self,
        filterable: FilterableDataSourcePort,
        filter_ids: list[str],
        filter_field: str,
        fallback_mapping: dict[str, str],
        limit: int | None,
    ) -> AsyncIterator[Any]:
        """Yield target records from a fallback-enabled upstream stream."""


class _FilterableTargetDelegationMixin:
    """Shared filterable delegation for wrappers exposing derived target entities."""

    def _ensure_filterable(
        self: _FilterableTargetWrapper,
        method_name: str,
    ) -> FilterableDataSourcePort:
        """Validate wrapped source implements FilterableDataSourcePort."""
        return _ensure_filterable_data_source(
            self._data_source,
            provider_name=self._data_source.provider_name,
            method_name=method_name,
        )

    async def fetch_filtered(
        self: _FilterableTargetWrapper,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None = None,
    ) -> AsyncIterator[Any]:
        """Fetch filtered records, deriving target records when requested."""
        filterable = self._ensure_filterable("fetch_filtered")
        async for record in _yield_target_or_delegate_records(
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
            yield record

    async def fetch_multi_filtered(
        self: _FilterableTargetWrapper,
        entity_type: str,
        filters: dict[str, list[str]],
        limit: int | None = None,
    ) -> AsyncIterator[Any]:
        """Fetch multi-filtered records, deriving target records when requested."""
        filterable = self._ensure_filterable("fetch_multi_filtered")
        async for record in _yield_target_or_delegate_records(
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
            yield record

    async def fetch_filtered_with_fallback(
        self: _FilterableTargetWrapper,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        fallback_mapping: dict[str, str],
        limit: int | None = None,
    ) -> AsyncIterator[Any]:
        """Fetch fallback-enabled records, deriving target records when requested."""
        filterable = self._ensure_filterable("fetch_filtered_with_fallback")
        async for record in _yield_target_or_delegate_records(
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
            yield record


def _ensure_filterable_data_source(
    data_source: object,
    *,
    provider_name: str,
    method_name: str,
) -> FilterableDataSourcePort:
    """Validate wrapped source implements FilterableDataSourcePort."""
    if not isinstance(data_source, FilterableDataSourcePort):
        raise TypeError(
            f"Wrapped adapter {provider_name} does not implement "
            f"FilterableDataSourcePort. {method_name}() requires a filterable adapter."
        )
    return data_source


async def _yield_target_or_delegate_records(
    *,
    entity_type: str,
    target_entity_type: str,
    target_factory: Callable[[], AsyncIterator[RecordT]],
    delegate_factory: Callable[[], AsyncIterator[RecordT]],
) -> AsyncIterator[RecordT]:
    """Yield target-derived records or delegate directly based on entity type."""
    iterator = (
        target_factory() if entity_type == target_entity_type else delegate_factory()
    )
    async for record in iterator:
        yield record
