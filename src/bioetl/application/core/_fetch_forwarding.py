"""Shared helpers for forwarding fetch arguments without duplicating kwargs blocks."""

from __future__ import annotations

from typing import Any

_UNSET_FETCH_ARG = object()


def build_forwarded_fetch_kwargs(
    *,
    entity_type: str,
    limit: int | None = None,
    query: str | None = None,
    filter_ids: list[str] | None | object = _UNSET_FETCH_ARG,
    filter_field: str | None | object = _UNSET_FETCH_ARG,
    offset: int | None = None,
) -> dict[str, Any]:
    """Build the canonical kwargs payload for forwarded fetch calls."""
    fetch_kwargs: dict[str, Any] = {
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
