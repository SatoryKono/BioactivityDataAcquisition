"""Fetch facade helpers for the CrossRef adapter."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from bioetl.domain.types import BronzeRecord
    from bioetl.infrastructure.adapters.crossref.fetch_flow import CrossRefFetchFlow
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient


__all__ = [
    "aclose_crossref_http_client",
    "fetch_crossref_publications",
    "fetch_crossref_publications_filtered",
    "fetch_crossref_publications_with_fallback",
    "raise_crossref_multifilter_not_supported",
]


async def fetch_crossref_publications_filtered(
    *,
    fetch_flow: CrossRefFetchFlow,
    entity_type: str,
    filter_ids: list[str],
    filter_field: str,
    limit: int | None = None,
) -> AsyncIterator[BronzeRecord]:
    """Delegate filtered CrossRef fetch to the configured fetch flow."""
    async for publication in fetch_flow.fetch_filtered(
        entity_type=entity_type,
        filter_ids=filter_ids,
        filter_field=filter_field,
        limit=limit,
    ):
        yield publication


async def fetch_crossref_publications_with_fallback(
    *,
    fetch_flow: CrossRefFetchFlow,
    entity_type: str,
    filter_ids: list[str],
    filter_field: str,
    fallback_mapping: dict[str, str],
    limit: int | None = None,
) -> AsyncIterator[BronzeRecord]:
    """Delegate filtered CrossRef fetch with title fallback to the fetch flow."""
    async for publication in fetch_flow.fetch_filtered_with_fallback(
        entity_type=entity_type,
        filter_ids=filter_ids,
        filter_field=filter_field,
        fallback_mapping=fallback_mapping,
        limit=limit,
    ):
        yield publication


async def fetch_crossref_publications(
    *,
    fetch_flow: CrossRefFetchFlow,
    entity_type: str,
    limit: int | None = None,
    query: str | None = None,
    filter_ids: list[str] | None = None,
    filter_field: str | None = None,
) -> AsyncIterator[BronzeRecord]:
    """Delegate general CrossRef fetch to the configured fetch flow."""
    async for publication in fetch_flow.fetch(
        entity_type=entity_type,
        limit=limit,
        query=query,
        filter_ids=filter_ids,
        filter_field=filter_field,
    ):
        yield publication


def raise_crossref_multifilter_not_supported() -> None:
    """Raise the canonical CrossRef multi-filter unsupported error."""
    raise NotImplementedError(
        "CrossRef API does not support multi-field filtering. "
        "Use fetch_filtered() with filter_field='doi' instead."
    )


async def aclose_crossref_http_client(
    *,
    http_client: UnifiedHTTPClient | None,
) -> None:
    """Close the adapter HTTP client when present."""
    if http_client:
        await http_client.__aexit__(None, None, None)
