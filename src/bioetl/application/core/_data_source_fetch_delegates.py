"""Shared fetch delegation entrypoints for application data sources."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.core._fetch_forwarding import forward_bound_fetch_records
from bioetl.application.core._target_data_source_fetch_support import (
    build_wrapped_fetch_kwargs,
    yield_wrapped_fetch_records_with_kwargs,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable

    from bioetl.domain.ports import DataSourcePort
    from bioetl.domain.types import JsonDict


def delegate_bound_fetch_records(
    instance: object,
    fetch_records: Callable[..., AsyncIterator[JsonDict]],
    *,
    entity_type: str,
    limit: int | None = None,
    query: str | None = None,
    filter_ids: list[str] | None = None,
    filter_field: str | None = None,
    offset: int | None = None,
) -> AsyncIterator[JsonDict]:
    """Forward a fetch call through a bound fetch_records helper."""
    return forward_bound_fetch_records(
        fetch_records,
        instance,
        entity_type=entity_type,
        limit=limit,
        query=query,
        filter_ids=filter_ids,
        filter_field=filter_field,
        offset=offset,
    )


def delegate_wrapped_data_source_fetch(
    data_source: DataSourcePort,
    *,
    entity_type: str,
    limit: int | None = None,
    query: str | None = None,
    filter_ids: list[str] | None = None,
    filter_field: str | None = None,
    offset: int | None = None,
) -> AsyncIterator[object]:
    """Delegate fetch to a wrapped data-source adapter."""
    return yield_wrapped_fetch_records_with_kwargs(
        data_source,
        build_wrapped_fetch_kwargs(
            entity_type=entity_type,
            limit=limit,
            query=query,
            filter_ids=filter_ids,
            filter_field=filter_field,
            offset=offset,
        ),
    )
