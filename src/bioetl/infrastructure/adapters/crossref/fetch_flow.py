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
    from bioetl.infrastructure.adapters.crossref.batch import (
        DoiBatchProcessor,
        SearchPaginator,
    )

__all__ = ["CrossRefFetchFlow"]


@dataclass(slots=True)
class CrossRefFetchFlow:
    """Orchestrates CrossRef FilterableDataSourcePort fetch and fallback paths."""

    logger: LoggerPort
    batch_fetcher: DoiBatchProcessor
    search_paginator: SearchPaginator
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
        """Fetch publications by DOI list (FilterableDataSourcePort contract)."""
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
        """Fetch publications by DOI with fallback search for misses."""
        validate_crossref_entity_type(entity_type)

        async def _primary_records(
            primary_ids: list[str], request_limit: int | None
        ) -> AsyncIterator[BronzeRecord]:
            for i in range(0, len(primary_ids), self.batch_size):
                if request_limit is not None and request_limit <= 0:
                    return
                batch = primary_ids[i : i + self.batch_size]
                async for publication in self.batch_fetcher.fetch_batch(batch):
                    yield publication

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
        """Fetch publications via DOI filtering or free-text query search."""
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
