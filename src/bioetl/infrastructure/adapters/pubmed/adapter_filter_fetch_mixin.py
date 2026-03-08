"""Filter/fetch orchestration mixin for PubMedAdapter.

Implements FilterableDataSourcePort contract for filtered API access.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from bioetl.domain.types import BronzeRecord

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.common import ComposableFallbackDecorator


async def _empty_async_iterator() -> AsyncIterator[BronzeRecord]:
    """Return an empty async iterator matching BronzeRecord stream contract."""
    if False:  # pragma: no cover
        yield {}


class _PubMedAdapterFilterFetchHost(Protocol):
    """Structural host contract for PubMed adapter fetch/filter behavior."""

    logger: LoggerPort
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


class PubMedAdapterFilterFetchMixin:
    """PubMed fetch/filter orchestration for FilterableDataSourcePort behavior."""

    async def fetch_filtered(
        self: _PubMedAdapterFilterFetchHost,
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
        if entity_type != "publication":
            raise ValueError("PubMedAdapter only supports 'publication'")

        if filter_field != "pmid":
            self.logger.warning(
                "unsupported_filter_field", field=filter_field, msg="Assuming PMIDs"
            )

        async for record in self._yield_articles_from_pmids(filter_ids, limit):
            record["_lookup_method"] = "pmid"
            yield record

    async def fetch_filtered_with_fallback(
        self: _PubMedAdapterFilterFetchHost,
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
        if entity_type != "publication":
            raise ValueError("PubMedAdapter only supports 'publication'")

        def _primary_records(
            primary_ids: list[str],
            request_limit: int | None,
        ) -> AsyncIterator[BronzeRecord]:
            if not primary_ids:
                return _empty_async_iterator()
            return self.fetch_filtered(
                entity_type=entity_type,
                filter_ids=primary_ids,
                filter_field=filter_field,
                limit=request_limit,
            )

        async for record in self._fallback_decorator.execute(
            filter_ids=filter_ids,
            fallback_mapping=fallback_mapping,
            primary_record_fetcher=_primary_records,
            limit=limit,
            filter_field=filter_field,
        ):
            yield record

    async def fetch(
        self: _PubMedAdapterFilterFetchHost,
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
        if filter_ids:
            async for record in self._fetch_from_filter_ids(
                entity_type=entity_type,
                filter_ids=filter_ids,
                filter_field=filter_field,
                limit=limit,
            ):
                yield record
            return

        self._validate_publication_entity(entity_type)
        resume_offset = self._resolve_resume_offset(limit=limit, offset=offset)
        if resume_offset is None:
            return

        pmids = await self._resolve_pmids_for_fetch(query=query, limit=limit)
        if not pmids:
            return

        pmids = self._apply_resume_offset(pmids=pmids, resume_offset=resume_offset)
        remaining_limit = None if limit is None else max(0, limit - resume_offset)
        async for record in self._yield_articles_from_pmids(pmids, remaining_limit):
            yield record

    async def _fetch_from_filter_ids(
        self: _PubMedAdapterFilterFetchHost,
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
        effective_filter_field = filter_field or "pmid"
        async for record in self.fetch_filtered(
            entity_type=entity_type,
            filter_ids=filter_ids,
            filter_field=effective_filter_field,
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
        if entity_type != "publication":
            raise ValueError("PubMedAdapter only supports 'publication'")

    def _resolve_resume_offset(
        self: _PubMedAdapterFilterFetchHost,
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
        resume_offset = max(0, offset or 0)
        if limit is not None and resume_offset >= limit:
            self.logger.info(
                "pubmed_resume_offset_reached_limit",
                offset=resume_offset,
                limit=limit,
            )
            return None
        return resume_offset

    async def _resolve_pmids_for_fetch(
        self: _PubMedAdapterFilterFetchHost,
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
        search_term = query or "pharmacogenomics[Title/Abstract]"
        return await self._get_pmids(search_term, limit or 10000)

    def _apply_resume_offset(
        self: _PubMedAdapterFilterFetchHost,
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
        if resume_offset == 0:
            return pmids
        self.logger.info(
            "pubmed_resume_skip_processed",
            offset=resume_offset,
            pmids_found=len(pmids),
        )
        return pmids[resume_offset:]


__all__ = ["PubMedAdapterFilterFetchMixin"]
