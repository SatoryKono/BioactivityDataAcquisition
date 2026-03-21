"""Filter/fetch orchestration mixin for PubMedAdapter.

Implements FilterableDataSourcePort contract for filtered API access.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.adapters.pubmed._filter_fetch_support import (
    PubMedAdapterFilterFetchHost,
    apply_resume_offset,
    fetch_filtered_records,
    fetch_filtered_with_fallback_records,
    fetch_from_filter_ids,
    fetch_records,
    resolve_pmids_for_fetch,
    resolve_resume_offset,
    validate_publication_entity,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


class PubMedAdapterFilterFetchMixin:
    """PubMed fetch/filter orchestration for FilterableDataSourcePort behavior."""

    async def fetch_filtered(
        self: PubMedAdapterFilterFetchHost,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch PubMed records by ID list via FilterableDataSourcePort contract.

        Args:
            entity_type: Entity type; must be "publication".
            filter_ids: List of PMID strings to fetch.
            filter_field: Filter field name; logs a warning if not "pmid".
            limit: Optional maximum number of records to yield.

        Yields:
            BronzeRecord articles with _lookup_method set to "pmid".

        Raises:
            ValueError: If entity_type is not "publication".
        """
        async for record in fetch_filtered_records(
            self,
            entity_type=entity_type,
            filter_ids=filter_ids,
            filter_field=filter_field,
            limit=limit,
        ):
            yield record

    async def fetch_filtered_with_fallback(
        self: PubMedAdapterFilterFetchHost,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        fallback_mapping: dict[str, str],
        limit: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch with fallback to title search when primary lookup fails.

        Args:
            entity_type: Entity type; must be "publication".
            filter_ids: List of PMID strings for primary batch resolution.
            filter_field: Filter field name used for the primary lookup phase.
            fallback_mapping: Mapping of PMID to title for title-based fallback.
            limit: Optional maximum number of records to yield.

        Yields:
            BronzeRecord articles from primary PMID resolution and title fallback phases.

        Raises:
            ValueError: If entity_type is not "publication".
        """
        async for record in fetch_filtered_with_fallback_records(
            self,
            entity_type=entity_type,
            filter_ids=filter_ids,
            filter_field=filter_field,
            fallback_mapping=fallback_mapping,
            limit=limit,
        ):
            yield record

    async def fetch(
        self: PubMedAdapterFilterFetchHost,
        entity_type: str,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
        offset: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch PubMed records.

        Args:
            entity_type: Entity type; must be "publication".
            limit: Optional maximum number of records to yield.
            query: Optional Entrez search query string.
            filter_ids: Optional list of PMIDs to filter by.
            filter_field: Optional filter field name; defaults to "pmid".
            offset: Optional record offset for resuming a previous fetch.

        Yields:
            BronzeRecord articles from the PubMed API.

        Raises:
            ValueError: If entity_type is not "publication".
        """
        async for record in fetch_records(
            self,
            entity_type=entity_type,
            limit=limit,
            query=query,
            filter_ids=filter_ids,
            filter_field=filter_field,
            offset=offset,
        ):
            yield record

    async def _fetch_from_filter_ids(
        self: PubMedAdapterFilterFetchHost,
        *,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str | None,
        limit: int | None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch records from explicit PMID filters.

        Args:
            entity_type: Entity type identifier.
            filter_ids: List of PMID strings to fetch.
            filter_field: Filter field name; defaults to "pmid" if None.
            limit: Optional maximum number of records to yield.

        Yields:
            BronzeRecord articles resolved from the filter IDs.
        """
        async for record in fetch_from_filter_ids(
            self,
            entity_type=entity_type,
            filter_ids=filter_ids,
            filter_field=filter_field,
            limit=limit,
        ):
            yield record

    @staticmethod
    def _validate_publication_entity(entity_type: str) -> None:
        """Validate supported PubMed entity type.

        Args:
            entity_type: Entity type string to validate.

        Raises:
            ValueError: If entity_type is not "publication".
        """
        validate_publication_entity(entity_type)

    def _resolve_resume_offset(
        self: PubMedAdapterFilterFetchHost,
        *,
        limit: int | None,
        offset: int | None,
    ) -> int | None:
        """Resolve and validate resume offset against limit.

        Args:
            limit: Optional total record limit for the fetch operation.
            offset: Optional starting offset for resuming a previous fetch.

        Returns:
            Validated resume offset integer, or None if offset has already reached the limit.
        """
        return resolve_resume_offset(self, limit=limit, offset=offset)

    async def _resolve_pmids_for_fetch(
        self: PubMedAdapterFilterFetchHost,
        *,
        query: str | None,
        limit: int | None,
    ) -> list[str]:
        """Fetch PMID list for current query/limit settings.

        Args:
            query: Optional Entrez search query string; defaults to pharmacogenomics query.
            limit: Optional maximum number of PMIDs to retrieve.

        Returns:
            List of PMID strings resolved from the search query or default term.
        """
        return await resolve_pmids_for_fetch(self, query=query, limit=limit)

    def _apply_resume_offset(
        self: PubMedAdapterFilterFetchHost,
        *,
        pmids: list[str],
        resume_offset: int,
    ) -> list[str]:
        """Skip already processed PMIDs when resuming.

        Args:
            pmids: Full list of PMIDs resolved for the current fetch operation.
            resume_offset: Number of leading entries to skip.

        Returns:
            PMID list with the first resume_offset entries removed.
        """
        return apply_resume_offset(
            self,
            pmids=pmids,
            resume_offset=resume_offset,
        )


__all__ = ["PubMedAdapterFilterFetchMixin"]
