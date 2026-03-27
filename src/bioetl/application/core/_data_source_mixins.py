"""Shared mixins for application data source wrappers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, Self, TypeVar

from bioetl.domain.ports import FilterableDataSourcePort

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable
    from types import TracebackType

    from bioetl.domain.ports import DataSourcePort
    from bioetl.domain.types import HealthStatus

RecordT = TypeVar("RecordT")
_UNSET_FETCH_ARG = object()


class _HasWrappedDataSource(Protocol):
    """Structural protocol for application classes that wrap a data source adapter.

    Used as a self-type constraint in mixin methods that need to access
    the wrapped ``_data_source`` attribute without inheriting from a concrete class.
    Conforms to the Ports and Adapters pattern (Hexagonal Architecture) where the
    application layer delegates to an injected infrastructure adapter.

    Attributes:
        _data_source: The wrapped data source adapter instance.
    """

    _data_source: DataSourcePort


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


class _WrappedDataSourceDelegationMixin:
    """Common delegation for wrappers around a DataSourcePort adapter."""

    @property
    def provider_name(self: _HasWrappedDataSource) -> str:
        """Provider name from the wrapped data source."""
        return self._data_source.provider_name

    async def __aenter__(self: _HasWrappedDataSource) -> Self:  # type: ignore
        """Enter async context and allow subclasses to reset wrapper state."""
        await self._data_source.__aenter__()
        self._after_wrapped_data_source_enter()  # type: ignore
        return self  # type: ignore

    def _after_wrapped_data_source_enter(self) -> None:
        """Hook for subclasses that need to reset state after adapter enter."""

    async def __aexit__(
        self: _HasWrappedDataSource,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Delegate async context teardown to the wrapped data source."""
        await self._data_source.__aexit__(exc_type, exc_val, exc_tb)

    async def health_check(self: _HasWrappedDataSource) -> HealthStatus:
        """Delegate health checks to the wrapped data source."""
        return await self._data_source.health_check()

    async def aclose(self: _HasWrappedDataSource) -> None:
        """Delegate resource shutdown to the wrapped data source."""
        await self._data_source.aclose()


class _TargetEntityFetchWrapper(Protocol[RecordT]):  # type: ignore
    """Structural contract for wrappers deriving a target entity from a source."""

    _data_source: DataSourcePort
    TARGET_ENTITY_TYPE: str

    async def _fetch_target_records(
        self,
        limit: int | None,
        query: str | None,
        filter_ids: list[str] | None,
        filter_field: str | None,
        offset: int | None,
    ) -> AsyncIterator[RecordT]:
        """Yield target records derived from the wrapped source."""


class _TargetEntityFetchDelegationMixin:
    """Shared fetch target-or-delegate behavior for derived entity wrappers."""

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
            return self._fetch_target_records(  # type: ignore
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


class _FilterableTargetWrapper(Protocol[RecordT]):  # type: ignore
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
    ) -> AsyncIterator[RecordT]:
        """Yield target records from a filtered upstream stream."""

    async def _fetch_target_multi_filtered_records(
        self,
        filterable: FilterableDataSourcePort,
        filters: dict[str, list[str]],
        limit: int | None,
    ) -> AsyncIterator[RecordT]:
        """Yield target records from a multi-filtered upstream stream."""

    async def _fetch_target_filtered_with_fallback_records(
        self,
        filterable: FilterableDataSourcePort,
        filter_ids: list[str],
        filter_field: str,
        fallback_mapping: dict[str, str],
        limit: int | None,
    ) -> AsyncIterator[RecordT]:
        """Yield target records from a fallback-enabled upstream stream."""


class _FallbackFilterableTargetWrapper(Protocol[RecordT]):  # type: ignore
    """Structural contract for target wrappers with shared fallback behavior."""

    SOURCE_ENTITY_TYPE: str

    def _resolve_target_fallback_upstream_limit(
        self,
        limit: int | None,
    ) -> int | None:
        """Resolve upstream source-record limit for fallback fetches."""

    def _yield_target_records_from_fallback_source_records(
        self,
        source_records: AsyncIterator[object],
        limit: int | None,
    ) -> AsyncIterator[RecordT]:
        """Transform fallback-fetched source records into target records."""


class _FilterableTargetDelegationMixin:
    """Shared filterable delegation for wrappers exposing derived target entities."""

    def _ensure_filterable(
        self: _FilterableTargetWrapper[RecordT],
        method_name: str,
    ) -> FilterableDataSourcePort:
        """Validate wrapped source implements FilterableDataSourcePort."""
        return _ensure_filterable_data_source(
            self._data_source,
            provider_name=self._data_source.provider_name,  # type: ignore
            method_name=method_name,
        )

    async def fetch_filtered(
        self: _FilterableTargetWrapper,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None = None,
    ) -> AsyncIterator[RecordT]:
        """Fetch filtered records, deriving target records when requested."""
        filterable = self._ensure_filterable("fetch_filtered")  # type: ignore
        async for record in _yield_target_or_delegate_records(
            entity_type=entity_type,
            target_entity_type=self.TARGET_ENTITY_TYPE,
            target_factory=lambda: self._fetch_target_filtered_records(  # type: ignore
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
        self: _FilterableTargetWrapper[RecordT],
        entity_type: str,
        filters: dict[str, list[str]],
        limit: int | None = None,
    ) -> AsyncIterator[RecordT]:
        """Fetch multi-filtered records, deriving target records when requested."""
        filterable = self._ensure_filterable("fetch_multi_filtered")  # type: ignore
        async for record in _yield_target_or_delegate_records(
            entity_type=entity_type,
            target_entity_type=self.TARGET_ENTITY_TYPE,
            target_factory=lambda: self._fetch_target_multi_filtered_records(  # type: ignore
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
        self: _FilterableTargetWrapper[RecordT],
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        fallback_mapping: dict[str, str],
        limit: int | None = None,
    ) -> AsyncIterator[RecordT]:
        """Fetch fallback-enabled records, deriving target records when requested."""
        filterable = self._ensure_filterable("fetch_filtered_with_fallback")  # type: ignore
        async for record in _yield_target_or_delegate_records(
            entity_type=entity_type,
            target_entity_type=self.TARGET_ENTITY_TYPE,
            target_factory=lambda: self._fetch_target_filtered_with_fallback_records(  # type: ignore
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


class _FallbackFilterableTargetFetchMixin:
    """Shared fallback-fetch implementation for derived target wrappers."""

    def _fetch_target_filtered_with_fallback_records(
        self: _FallbackFilterableTargetWrapper[RecordT],
        filterable: FilterableDataSourcePort,
        filter_ids: list[str],
        filter_field: str,
        fallback_mapping: dict[str, str],
        limit: int | None,
    ) -> AsyncIterator[RecordT]:
        """Yield target records from fallback-enabled upstream records."""
        return _yield_target_records_from_fallback_fetch(
            filterable,
            source_entity_type=self.SOURCE_ENTITY_TYPE,
            filter_ids=filter_ids,
            filter_field=filter_field,
            fallback_mapping=fallback_mapping,
            upstream_limit=self._resolve_target_fallback_upstream_limit(limit),
            limit=limit,
            target_yielder=self._yield_target_records_from_fallback_source_records,
        )


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


async def _yield_wrapped_fetch_records(
    data_source: DataSourcePort,
    *,
    entity_type: str,
    limit: int | None = None,
    query: str | None = None,
    filter_ids: list[str] | None | object = _UNSET_FETCH_ARG,
    filter_field: str | None | object = _UNSET_FETCH_ARG,
    offset: int | None = None,
) -> AsyncIterator[RecordT]:
    """Delegate a plain fetch call to a wrapped data source adapter."""
    fetch_kwargs: dict[str, object] = {
        "entity_type": entity_type,
        "limit": limit,
        "query": query,
        "offset": offset,
    }
    if filter_ids is not _UNSET_FETCH_ARG:
        fetch_kwargs["filter_ids"] = filter_ids
    if filter_field is not _UNSET_FETCH_ARG:
        fetch_kwargs["filter_field"] = filter_field
    async for record in data_source.fetch(**fetch_kwargs):  # type: ignore
        yield record  # type: ignore


def _yield_plain_wrapped_fetch_records(
    data_source: DataSourcePort,
    *,
    entity_type: str,
    limit: int | None = None,
    query: str | None = None,
    offset: int | None = None,
) -> AsyncIterator[RecordT]:
    """Delegate a plain unfiltered fetch call to a wrapped adapter."""
    return _yield_wrapped_fetch_records(
        data_source,
        entity_type=entity_type,
        limit=limit,
        query=query,
        offset=offset,
    )


def _yield_target_records_from_fallback_fetch(
    filterable: FilterableDataSourcePort,
    *,
    source_entity_type: str,
    filter_ids: list[str],
    filter_field: str,
    fallback_mapping: dict[str, str],
    upstream_limit: int | None,
    limit: int | None,
    target_yielder: Callable[
        [AsyncIterator[object], int | None], AsyncIterator[RecordT]
    ],
) -> AsyncIterator[RecordT]:
    """Transform fallback-enabled upstream fetches into target records."""
    return target_yielder(
        filterable.fetch_filtered_with_fallback(
            entity_type=source_entity_type,
            filter_ids=filter_ids,
            filter_field=filter_field,
            fallback_mapping=fallback_mapping,
            limit=upstream_limit,
        ),
        limit,
    )


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
