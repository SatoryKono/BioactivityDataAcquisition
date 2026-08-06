"""Fetch orchestration flow for CrossRef FilterableDataSourcePort facade."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.adapters.crossref.query_builder import (
    resolve_filter_field,
    validate_crossref_entity_type,
)
from bioetl.infrastructure.adapters.crossref.response_mapper import (
    CrossRefResponseMapper,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.common import ComposableFallbackDecorator
    from bioetl.infrastructure.adapters.crossref.types import (
        CrossRefBatchFetcher,
        CrossRefSearchPaginator,
    )

__all__ = ["CrossRefFetchFlow"]


@dataclass(slots=True)
class CrossRefFetchFlow:
    """Orchestrates CrossRef FilterableDataSourcePort fetch and fallback paths."""

    logger: LoggerPort
    batch_fetcher: CrossRefBatchFetcher
    search_paginator: CrossRefSearchPaginator
    fallback_decorator: ComposableFallbackDecorator
    batch_size: int
    response_mapper: CrossRefResponseMapper

    async def fetch_filtered(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch publications by DOI list (FilterableDataSourcePort contract).

        Args:
            entity_type: Entity type to validate (CrossRef only supports
                publication-type entities).
            filter_ids: List of DOIs to fetch.
            filter_field: Filter field name; only "doi" is supported.
                A warning is logged for unsupported values.
            limit: Maximum number of records to yield.

        Yields:
            Bronze records fetched from CrossRef by DOI batch.

        """
        validate_crossref_entity_type(entity_type)

        if filter_field != "doi":
            self.logger.warning(
                "unsupported_filter_field",
                field=filter_field,
                msg="CrossRef only supports DOI filtering, assuming DOIs",
            )

        dois = filter_ids[:limit] if limit else filter_ids
        fetched = 0
        for i in range(0, len(dois), self.batch_size):
            batch = dois[i : i + self.batch_size]
            async for publication in self.batch_fetcher.fetch_batch(batch):
                yield self.response_mapper.with_lookup_method(publication, "doi")
                fetched += 1
                if limit and fetched >= limit:
                    return

    async def fetch_filtered_with_fallback(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        fallback_mapping: dict[str, str],
        limit: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch publications by DOI with fallback search for misses.

        Args:
            entity_type: Entity type to validate against CrossRef-supported types.
            filter_ids: List of primary IDs (DOIs) to fetch.
            filter_field: Filter field name used to select fallback strategy.
            fallback_mapping: Mapping from DOI to title for fallback title search.
            limit: Maximum number of records to yield.

        Yields:
            Bronze records from primary DOI batch fetch and title-based fallback.

        """
        validate_crossref_entity_type(entity_type)

        async def _primary_records(
            primary_ids: list[str], request_limit: int | None
        ) -> AsyncIterator[BronzeRecord]:
            yielded = 0
            for i in range(0, len(primary_ids), self.batch_size):
                if request_limit is not None and yielded >= request_limit:
                    return
                batch = primary_ids[i : i + self.batch_size]
                async for publication in self.batch_fetcher.fetch_batch(batch):
                    yield self.response_mapper.with_lookup_method(
                        publication, "doi"
                    )
                    yielded += 1
                    if request_limit is not None and yielded >= request_limit:
                        return

        async for publication in self.fallback_decorator.execute(
            filter_ids=filter_ids,
            fallback_mapping=fallback_mapping,
            primary_record_fetcher=_primary_records,
            limit=limit,
            filter_field=filter_field,
        ):
            yield publication

    async def fetch(
        self,
        entity_type: str,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch publications via DOI filtering or free-text query search.

        If ``filter_ids`` are provided, delegates to ``fetch_filtered``.
        Otherwise uses the search paginator with the ``query`` parameter.

        Args:
            entity_type: Entity type to fetch (must be a CrossRef-supported type).
            limit: Maximum number of records to yield.
            query: Free-text search query (required when ``filter_ids`` is empty).
            filter_ids: Optional list of DOIs to fetch by ID.
            filter_field: Filter field name (defaults to "doi" when filter_ids given).

        Raises:
            ValueError: If neither ``filter_ids`` nor ``query`` is provided.

        Yields:
            Bronze records from CrossRef API.

        """
        if filter_ids:
            effective_filter_field = resolve_filter_field(filter_field)
            async for publication in self.fetch_filtered(
                entity_type=entity_type,
                filter_ids=filter_ids,
                filter_field=effective_filter_field,
                limit=limit,
            ):
                yield publication
            return

        validate_crossref_entity_type(entity_type)
        if not query:
            raise ValueError(
                "CrossRef requires either filter_ids (DOIs) or query parameter"
            )
        async for publication in self.search_paginator.search(query, limit):
            yield publication
