# mypy: disable-error-code=attr-defined
"""Fetch and fallback entrypoints for SemanticScholarAdapter.

Contains FilterableDataSourcePort-compatible filtering methods.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, cast

from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.adapters.filterable_mixin import raising_async_iterator
from bioetl.infrastructure.adapters.semanticscholar._search_fetch_flow import (
    _SemanticScholarSearchFetchMixin,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


class SemanticScholarFetchAdapterMixin(_SemanticScholarSearchFetchMixin):
    """Public fetch/filter/fallback paths extracted from adapter facade."""

    async def fetch(
        self,
        entity_type: str,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
        offset: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch records via search endpoint or delegated filtered path.

        Args:
            entity_type: Entity type to fetch; must be "publication" or "paper".
            limit: Optional maximum number of records to yield.
            query: Optional query string for the search endpoint.
            filter_ids: Optional list of DOIs to resolve via batch endpoint.
            filter_field: Optional filter field name; defaults to "doi" when filter_ids provided.
            offset: Ignored; internal pagination manages offset automatically.

        Yields:
            BronzeRecord entries from the Semantic Scholar API.

        Raises:
            ValueError: If entity_type is not "publication" or "paper".
        """
        del offset
        if filter_ids:
            async for record in self._fetch_from_filter_ids(
                entity_type=entity_type,
                filter_ids=filter_ids,
                filter_field=filter_field,
                limit=limit,
            ):
                yield record
            return

        self._validate_entity_type(entity_type)
        async for record in self._paginate_search(query=query, limit=limit):
            yield record

    async def _fetch_from_filter_ids(
        self,
        *,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str | None,
        limit: int | None,
    ) -> AsyncIterator[BronzeRecord]:
        """Delegate filtered fetch path.

        Args:
            entity_type: Entity type to fetch.
            filter_ids: List of IDs to filter by.
            filter_field: Filter field name; defaults to "doi" if None.
            limit: Optional maximum number of records to yield.

        Yields:
            BronzeRecord entries resolved from the filter IDs.
        """
        effective_filter_field = filter_field or "doi"
        async for record in self.fetch_filtered(
            entity_type=entity_type,
            filter_ids=filter_ids,
            filter_field=effective_filter_field,
            limit=limit,
        ):
            yield record

    async def fetch_filtered(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Batch DOI resolution via POST /paper/batch.

        Args:
            entity_type: Entity type identifier (ignored; always resolves publications).
            filter_ids: List of DOI strings to resolve via batch endpoint.
            filter_field: Filter field name; logs a warning if not "doi".
            limit: Optional maximum number of records to yield.

        Yields:
            BronzeRecord entries resolved from the batch DOI lookup.
        """
        del entity_type
        if filter_field != "doi":
            self._logger.warning(
                "unsupported_filter_field",
                field=filter_field,
                expected="doi",
            )

        dois = filter_ids[:limit] if limit else filter_ids
        fetched = 0

        concurrency_limit = 5

        for chunk_idx in range(0, len(dois), self.batch_size * concurrency_limit):
            chunk_dois = dois[
                chunk_idx : chunk_idx + self.batch_size * concurrency_limit
            ]
            batches = [
                chunk_dois[i : i + self.batch_size]
                for i in range(0, len(chunk_dois), self.batch_size)
            ]

            tasks = [self._fetch_batch_with_nulls(batch) for batch in batches]
            results = await asyncio.gather(*tasks)

            for batch_results in results:
                for record in batch_results:
                    if record is not None:
                        record["_lookup_method"] = "doi"
                        yield record
                        fetched += 1
                        if limit and fetched >= limit:
                            return

    async def _batch_doi_phase(
        self,
        valid_dois: list[str],
        resolved_dois: set[str],
        limit: int | None,
        start_count: int,
    ) -> AsyncIterator[BronzeRecord]:
        """Phase-1 DOI resolution preserving unresolved markers.

        Args:
            valid_dois: List of DOI strings to resolve in the primary batch phase.
            resolved_dois: Mutable set updated in-place with successfully resolved DOIs.
            limit: Optional maximum total records to yield across all phases.
            start_count: Record count already yielded before this phase started.

        Yields:
            BronzeRecord entries from resolved DOIs with lookup metadata.
        """
        count = start_count
        concurrency_limit = 5

        for chunk_idx in range(0, len(valid_dois), self.batch_size * concurrency_limit):
            if limit and count >= limit:
                return

            chunk_dois = valid_dois[
                chunk_idx : chunk_idx + self.batch_size * concurrency_limit
            ]
            batches = [
                chunk_dois[i : i + self.batch_size]
                for i in range(0, len(chunk_dois), self.batch_size)
            ]

            tasks = [self._fetch_batch_with_nulls(batch) for batch in batches]
            results = await asyncio.gather(*tasks)

            for batch, batch_results in zip(batches, results, strict=True):
                for doi, record in zip(batch, batch_results, strict=True):
                    if record is None:
                        continue
                    resolved_dois.add(doi.lower())
                    record["_lookup_method"] = "doi"
                    record["_resolved_doi"] = doi
                    count += 1
                    yield record
                    if limit and count >= limit:
                        return

    async def fetch_filtered_with_fallback(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        fallback_mapping: dict[str, str],
        limit: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch by DOI and recover unresolved records through title fallback.

        Args:
            entity_type: Entity type identifier (ignored; always resolves publications).
            filter_ids: List of DOI strings for primary batch resolution.
            filter_field: Filter field name used for the primary lookup phase.
            fallback_mapping: Mapping of DOI to title for title-based fallback resolution.
            limit: Optional maximum number of records to yield.

        Yields:
            BronzeRecord entries from primary DOI resolution and title fallback phases.
        """
        del entity_type
        resolved_dois: set[str] = set()

        def _primary_records(
            primary_ids: list[str], request_limit: int | None
        ) -> AsyncIterator[BronzeRecord]:
            return self._batch_doi_phase(primary_ids, resolved_dois, request_limit, 0)

        def _extract_record_doi(record: BronzeRecord) -> str | None:
            resolved = record.pop("_resolved_doi", None)
            if isinstance(resolved, str) and resolved.strip():
                return cast("str | None", self._normalize_doi(resolved))
            return None

        async for record in self._fallback_decorator.execute(
            filter_ids=filter_ids,
            fallback_mapping=fallback_mapping,
            primary_record_fetcher=_primary_records,
            limit=limit,
            filter_field=filter_field,
            extract_record_id=_extract_record_doi,
        ):
            yield record

    def fetch_multi_filtered(
        self,
        entity_type: str,
        filters: dict[str, list[str]],
        limit: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Semantic Scholar does not support multi-field filtering.

        Args:
            entity_type: Entity type identifier (unused).
            filters: Multi-field filter mapping (unused; raises NotImplementedError).
            limit: Optional maximum record limit (unused; raises NotImplementedError).

        Raises:
            NotImplementedError: Always; Semantic Scholar supports only DOI filtering.
        """
        del entity_type, filters, limit
        return raising_async_iterator(
            NotImplementedError(
                "Semantic Scholar adapter supports only DOI filtering. "
                "Use fetch_filtered() or fetch_filtered_with_fallback()."
            )
        )
