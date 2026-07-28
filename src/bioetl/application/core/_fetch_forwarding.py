"""Shared helpers for forwarding fetch arguments without duplicating kwargs blocks."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable

from bioetl.domain.types import JsonDict

_UNSET_FETCH_ARG = object()

def build_forwarded_fetch_kwargs(
    *,
    entity_type: str,
    limit: int | None = None,
    query: str | None = None,
    filter_ids: list[str] | None | object = _UNSET_FETCH_ARG,
    filter_field: str | None | object = _UNSET_FETCH_ARG,
    offset: int | None = None,
) -> dict[str, object | None]:
    """Build the canonical kwargs payload for forwarded fetch calls."""
    fetch_kwargs: dict[str, object | None] = {
        "entity_type": entity_type,
        "limit": limit,
        "query": query,
        "offset": offset,
    }
    if filter_ids is not _UNSET_FETCH_ARG:
        fetch_kwargs["filter_ids"] = filter_ids
    if filter_field is not _UNSET_FETCH_ARG:
        fetch_kwargs["filter_field"] = filter_field
    return fetch_kwargs

async def forward_fetch_records(
    fetch_fn: Callable[..., AsyncIterator[JsonDict]],
    entity_type: str,
    limit: int | None = None,
    query: str | None = None,
    filter_ids: list[str] | None | object = _UNSET_FETCH_ARG,
    filter_field: str | None | object = _UNSET_FETCH_ARG,
    offset: int | None = None,
) -> AsyncIterator[JsonDict]:
    """Forward fetch arguments into a callable and yield the resulting records."""
    iterator = fetch_fn(
        **build_forwarded_fetch_kwargs(
            entity_type=entity_type,
            limit=limit,
            query=query,
            filter_ids=filter_ids,
            filter_field=filter_field,
            offset=offset,
        ),
    )
    async for record in iterator:
        yield record
