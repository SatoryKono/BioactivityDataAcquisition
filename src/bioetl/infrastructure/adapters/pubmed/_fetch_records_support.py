"""Query/filter dispatch entry for PubMed record fetching."""

from __future__ import annotations

from collections.abc import AsyncIterator

from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.adapters.pubmed._filter_fetch_support import (
    PubMedAdapterFilterFetchHost,
)


async def fetch_records(
    host: PubMedAdapterFilterFetchHost,
    *,
    entity_type: str,
    limit: int | None,
    query: str | None,
    filter_ids: list[str] | None,
    filter_field: str | None,
    offset: int | None,
) -> AsyncIterator[BronzeRecord]:
    """Fetch PubMed records through filtered or query-based path."""
    if filter_ids:
        async for record in host._fetch_from_filter_ids(
            entity_type=entity_type,
            filter_ids=filter_ids,
            filter_field=filter_field,
            limit=limit,
        ):
            yield record
        return

    host._validate_publication_entity(entity_type)
    resume_offset = host._resolve_resume_offset(limit=limit, offset=offset)
    if resume_offset is None:
        return

    pmids = await host._resolve_pmids_for_fetch(query=query, limit=limit)
    if not pmids:
        return

    pmids = host._apply_resume_offset(pmids=pmids, resume_offset=resume_offset)
    remaining_limit = None if limit is None else max(0, limit - resume_offset)
    async for record in host._yield_articles_from_pmids(pmids, remaining_limit):
        yield record
