"""Shared fetch-request construction for adapter decorators."""

from __future__ import annotations

from bioetl.infrastructure.adapters.decorators._data_source_delegation import (
    DataSourceFetchRequest,
)

__all__ = ["build_data_source_fetch_request"]


def build_data_source_fetch_request(
    *,
    entity_type: str,
    limit: int | None = None,
    query: str | None = None,
    filter_ids: list[str] | None = None,
    filter_field: str | None = None,
    offset: int | None = None,
) -> DataSourceFetchRequest:
    """Build the canonical fetch request payload for decorator wrappers."""
    return DataSourceFetchRequest(
        entity_type=entity_type,
        limit=limit,
        query=query,
        filter_ids=filter_ids,
        filter_field=filter_field,
        offset=offset,
    )
