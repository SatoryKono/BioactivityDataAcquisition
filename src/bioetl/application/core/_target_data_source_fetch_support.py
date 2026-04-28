"""Private fetch-delegation helpers for derived target data-source wrappers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar, cast

from bioetl.application.core._fetch_forwarding import (
    _UNSET_FETCH_ARG,
    build_forwarded_fetch_kwargs,
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
    *,
    entity_type: str,
    limit: int | None = None,
    query: str | None = None,
    filter_ids: list[str] | None | object = _UNSET_FETCH_ARG,
    filter_field: str | None | object = _UNSET_FETCH_ARG,
    offset: int | None = None,
) -> AsyncIterator[RecordT]:
    """Delegate a plain fetch call to a wrapped data source adapter."""
    iterator = cast(
        "AsyncIterator[RecordT]",
        cast(
            "Any",  # Any: Dynamic data source adapter
            data_source,
        ).fetch(
            **build_forwarded_fetch_kwargs(
                entity_type=entity_type,
                limit=limit,
                query=query,
                filter_ids=filter_ids,
                filter_field=filter_field,
                offset=offset,
            ),
        ),
    )
    async for record in iterator:
        yield record


def yield_plain_wrapped_fetch_records(
    data_source: DataSourcePort,
    *,
    entity_type: str,
    limit: int | None = None,
    query: str | None = None,
    offset: int | None = None,
) -> AsyncIterator[RecordT]:
    """Delegate a plain unfiltered fetch call to a wrapped adapter."""
    return yield_wrapped_fetch_records(
        data_source,
        entity_type=entity_type,
        limit=limit,
        query=query,
        offset=offset,
    )


def yield_target_records_from_fallback_fetch(
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


async def yield_target_or_delegate_records(
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
