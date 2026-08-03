"""Private fetch-delegation helpers for derived target data-source wrappers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar, cast

from bioetl.application.core._fetch_forwarding import (
    _UNSET_FETCH_ARG,
    forward_fetch_records,
)
from bioetl.domain.ports import FilterableDataSourcePort

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable

    from bioetl.domain.ports import DataSourcePort

RecordT = TypeVar("RecordT")


def ensure_filterable_data_source(
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


async def yield_wrapped_fetch_records(
    data_source: DataSourcePort,
    entity_type: str,
    limit: int | None = None,
    query: str | None = None,
    filter_ids: list[str] | object | None = _UNSET_FETCH_ARG,
    filter_field: str | object | None = _UNSET_FETCH_ARG,
    offset: int | None = None,
) -> AsyncIterator[RecordT]:
    """Delegate a plain fetch call to a wrapped data source adapter."""
    async for record in forward_fetch_records(
        cast(
            "Any",  # Any: Dynamic data source adapter
            data_source,
        ).fetch,
        entity_type,
        limit,
        query,
        filter_ids,
        filter_field,
        offset,
    ):
        yield cast("RecordT", record)


def yield_plain_wrapped_fetch_records(
    data_source: DataSourcePort,
    entity_type: str,
    limit: int | None = None,
    query: str | None = None,
    offset: int | None = None,
) -> AsyncIterator[RecordT]:
    """Delegate a plain unfiltered fetch call to a wrapped adapter."""
    return yield_wrapped_fetch_records(
        data_source,
        entity_type,
        limit,
        query,
        _UNSET_FETCH_ARG,
        _UNSET_FETCH_ARG,
        offset,
    )


def yield_target_records_from_fallback_fetch[RecordT](
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


async def yield_target_or_delegate_records[RecordT](
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
