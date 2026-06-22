"""Shared helpers for forwarding fetch arguments without duplicating kwargs blocks."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Mapping

from bioetl.domain.types import JsonDict

_UNSET_FETCH_ARG = object()
_FORWARDED_FETCH_KWARG_NAMES = (
    "entity_type",
    "limit",
    "query",
    "filter_ids",
    "filter_field",
    "offset",
)


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


def build_forwarded_fetch_kwargs_from_mapping(
    values: Mapping[str, object],
) -> dict[str, object | None]:
    """Build forwarded fetch kwargs from a same-named locals()/mapping payload."""
    return build_forwarded_fetch_kwargs(
        **{
            field_name: values.get(field_name, _UNSET_FETCH_ARG)
            for field_name in _FORWARDED_FETCH_KWARG_NAMES
        }
    )


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


def forward_bound_fetch_records[RecordT](
    fetch_records: Callable[..., AsyncIterator[RecordT]],
    bound_instance: object,
    entity_type: str,
    limit: int | None = None,
    query: str | None = None,
    filter_ids: list[str] | None | object = _UNSET_FETCH_ARG,
    filter_field: str | None | object = _UNSET_FETCH_ARG,
    offset: int | None = None,
) -> AsyncIterator[RecordT]:
    """Forward fetch arguments into a bound fetch_records helper."""

    async def _forward() -> AsyncIterator[RecordT]:
        iterator = fetch_records(
            bound_instance,
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

    return _forward()


def delegate_bound_fetch_records[RecordT](
    fetch_records: Callable[..., AsyncIterator[RecordT]],
    bound_instance: object,
    entity_type: str,
    limit: int | None = None,
    query: str | None = None,
    filter_ids: list[str] | None | object = _UNSET_FETCH_ARG,
    filter_field: str | None | object = _UNSET_FETCH_ARG,
    offset: int | None = None,
) -> AsyncIterator[RecordT]:
    """Delegate fetch through a canonical bound fetch_records helper."""
    return forward_bound_fetch_records(
        fetch_records,
        bound_instance,
        entity_type=entity_type,
        limit=limit,
        query=query,
        filter_ids=filter_ids,
        filter_field=filter_field,
        offset=offset,
    )
