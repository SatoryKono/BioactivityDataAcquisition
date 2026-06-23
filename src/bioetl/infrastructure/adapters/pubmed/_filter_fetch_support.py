"""Internal support helpers for PubMed filter/fetch orchestration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, cast

from bioetl.domain.types import BronzeRecord

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.common import ComposableFallbackDecorator


_PUBLICATION_ONLY_ERROR = "PubMedAdapter only supports 'publication'"


async def empty_async_iterator() -> AsyncIterator[BronzeRecord]:
    """Return an empty async iterator matching BronzeRecord stream contract."""
    for record in cast(tuple[BronzeRecord, ...], ()):
        yield record


class PubMedAdapterFilterFetchHost(Protocol):
    """Structural host contract for PubMed adapter fetch/filter behavior."""

    logger: LoggerPort
    _logger: LoggerPort
    _fallback_decorator: ComposableFallbackDecorator

    def _yield_articles_from_pmids(
        self,
        pmids: list[str],
        limit: int | None,
    ) -> AsyncIterator[BronzeRecord]:
        """Yield normalized article records from PMID values."""
        ...

    def fetch_filtered(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch records by filter IDs."""
        ...

    def _fetch_from_filter_ids(
        self,
        *,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str | None,
        limit: int | None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch from explicit filter IDs."""
        ...

    @staticmethod
    def _validate_publication_entity(entity_type: str) -> None:
        """Validate supported entity type."""
        ...

    def _resolve_resume_offset(
        self,
        *,
        limit: int | None,
        offset: int | None,
    ) -> int | None:
        """Resolve resume offset."""
        ...

    async def _resolve_pmids_for_fetch(
        self,
        *,
        query: str | None,
        limit: int | None,
    ) -> list[str]:
        """Resolve PMIDs for current fetch request."""
        ...

    def _apply_resume_offset(
        self,
        *,
        pmids: list[str],
        resume_offset: int,
    ) -> list[str]:
        """Apply resume offset to PMID list."""
        ...

    async def _get_pmids(self, search_term: str, max_count: int) -> list[str]:
        """Resolve PMIDs through Entrez search endpoint."""
        ...


async def fetch_filtered_records(
    host: PubMedAdapterFilterFetchHost,
    *,
    entity_type: str,
    filter_ids: list[str],
    filter_field: str,
    limit: int | None,
) -> AsyncIterator[BronzeRecord]:
    """Fetch PubMed records by ID list via FilterableDataSourcePort contract."""
    if entity_type != "publication":
        raise ValueError(_PUBLICATION_ONLY_ERROR)

    if filter_field != "pmid":
        host._logger.warning(
            "unsupported_filter_field", field=filter_field, msg="Assuming PMIDs"
        )

    async for record in host._yield_articles_from_pmids(filter_ids, limit):
        record["_lookup_method"] = "pmid"
        yield record


async def fetch_filtered_with_fallback_records(
    host: PubMedAdapterFilterFetchHost,
    *,
    entity_type: str,
    filter_ids: list[str],
    filter_field: str,
    fallback_mapping: dict[str, str],
    limit: int | None,
) -> AsyncIterator[BronzeRecord]:
    """Fetch with fallback to title search when primary lookup fails."""
    if entity_type != "publication":
        raise ValueError(_PUBLICATION_ONLY_ERROR)

    def _primary_records(
        primary_ids: list[str],
        request_limit: int | None,
    ) -> AsyncIterator[BronzeRecord]:
        if not primary_ids:
            return empty_async_iterator()
        return host.fetch_filtered(
            entity_type=entity_type,
            filter_ids=primary_ids,
            filter_field=filter_field,
            limit=request_limit,
        )

    async for record in host._fallback_decorator.execute(
        filter_ids=filter_ids,
        fallback_mapping=fallback_mapping,
        primary_record_fetcher=_primary_records,
        limit=limit,
        filter_field=filter_field,
    ):
        yield record


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


async def fetch_from_filter_ids(
    host: PubMedAdapterFilterFetchHost,
    *,
    entity_type: str,
    filter_ids: list[str],
    filter_field: str | None,
    limit: int | None,
) -> AsyncIterator[BronzeRecord]:
    """Fetch records from explicit PMID filters."""
    effective_filter_field = filter_field or "pmid"
    async for record in host.fetch_filtered(
        entity_type=entity_type,
        filter_ids=filter_ids,
        filter_field=effective_filter_field,
        limit=limit,
    ):
        yield record


def validate_publication_entity(entity_type: str) -> None:
    """Validate supported PubMed entity type."""
    if entity_type != "publication":
        raise ValueError(_PUBLICATION_ONLY_ERROR)


def resolve_resume_offset(
    host: PubMedAdapterFilterFetchHost,
    *,
    limit: int | None,
    offset: int | None,
) -> int | None:
    """Resolve and validate resume offset against limit."""
    resume_offset = max(0, offset or 0)
    if limit is not None and resume_offset >= limit:
        host._logger.info(
            "pubmed_resume_offset_reached_limit",
            offset=resume_offset,
            limit=limit,
        )
        return None
    return resume_offset


async def resolve_pmids_for_fetch(
    host: PubMedAdapterFilterFetchHost,
    *,
    query: str | None,
    limit: int | None,
) -> list[str]:
    """Fetch PMID list for current query/limit settings."""
    search_term = query or "pharmacogenomics[Title/Abstract]"
    return await host._get_pmids(search_term, limit or 10000)


def apply_resume_offset(
    host: PubMedAdapterFilterFetchHost,
    *,
    pmids: list[str],
    resume_offset: int,
) -> list[str]:
    """Skip already processed PMIDs when resuming."""
    if resume_offset == 0:
        return pmids
    host._logger.info(
        "pubmed_resume_skip_processed",
        offset=resume_offset,
        pmids_found=len(pmids),
    )
    return pmids[resume_offset:]
