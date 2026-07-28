# mypy: disable-error-code=attr-defined
# pyright: reportAttributeAccessIssue=false
# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
"""Filtered/fallback fetch methods for UniProtAdapter.

Contains FilterableDataSourcePort-compatible filtering methods.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable

from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.adapters.common.deduplication import (
    deduplicate_preserving_order,
)
from bioetl.infrastructure.adapters.uniprot.fallback_policy import (
    UniProtFallbackPolicy,
)
from bioetl.infrastructure.adapters.uniprot.fallback_resolver import (
    iter_uniprot_fallback_records,
    resolve_uniprot_missing_ids,
)

_FetchStrategy = Callable[..., AsyncIterator[BronzeRecord]]

_UNIPROT_FILTER_BATCH_SIZE = 100


class UniProtFilteringAdapterMixin:
    """Filtering and fallback orchestration extracted from UniProtAdapter."""

    async def _fetch_non_protein_filtered(
        self,
        strategy: _FetchStrategy,
        filter_ids: list[str],
        limit: int | None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch non-protein entities by per-ID query."""
        fetched = 0
        for accession_id in filter_ids:
            if limit and fetched >= limit:
                break
            async for record in strategy(query=accession_id, limit=1):
                yield record
                fetched += 1
                if limit and fetched >= limit:
                    break

    async def _fetch_proteins_batched(
        self,
        strategy: _FetchStrategy,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch protein entities using batched OR query."""
        fetched = 0
        for batch_start in range(0, len(filter_ids), _UNIPROT_FILTER_BATCH_SIZE):
            if limit and fetched >= limit:
                break

            batch = filter_ids[batch_start : batch_start + _UNIPROT_FILTER_BATCH_SIZE]
            or_query = " OR ".join(f"{filter_field}:{acc}" for acc in batch)
            batch_limit = (limit - fetched) if limit else None
            async for record in strategy(query=or_query, limit=batch_limit):
                yield record
                fetched += 1
                if limit and fetched >= limit:
                    return

    async def fetch_filtered(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch records filtered by entity-specific IDs."""
        if not filter_ids:
            return

        strategy = self._fetch_strategies.get(entity_type)
        if not strategy:
            raise ValueError(
                f"Unsupported entity type: {entity_type}. "
                f"Supported: {', '.join(self._fetch_strategies.keys())}"
            )

        if entity_type != "protein":
            async for record in self._fetch_non_protein_filtered(
                strategy, filter_ids, limit
            ):
                yield record
            return

        async for record in self._fetch_proteins_batched(
            strategy, filter_ids, filter_field, limit
        ):
            yield record

    async def fetch_multi_filtered(
        self,
        entity_type: str,
        filters: dict[str, list[str]],
        limit: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch records matching combined filter conditions."""
        if not filters:
            return

        strategy = self._fetch_strategies.get(entity_type)
        if not strategy:
            raise ValueError(
                f"Unsupported entity type: {entity_type}. "
                f"Supported: {', '.join(self._fetch_strategies.keys())}"
            )

        and_parts: list[str] = []
        for field, ids in filters.items():
            if not ids:
                continue
            and_parts.append(f"({' OR '.join(f'{field}:{value}' for value in ids)})")

        if not and_parts:
            return

        combined_query = " AND ".join(and_parts)
        async for record in strategy(query=combined_query, limit=limit):
            yield record

    async def _do_fallback_search(
        self,
        entity_type: str,
        missing_ids: list[str],
        fallback_mapping: dict[str, str],
        limit: int | None,
        already_fetched: int,
    ) -> AsyncIterator[BronzeRecord]:
        """Search unresolved IDs using fallback mapping."""
        strategy = self._fetch_strategies.get(entity_type)
        if not strategy:
            return

        async for record in iter_uniprot_fallback_records(
            strategy=strategy,
            missing_ids=missing_ids,
            fallback_mapping=fallback_mapping,
            limit=limit,
            already_fetched=already_fetched,
        ):
            yield record

    async def _do_primary_fetch(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None,
    ) -> AsyncIterator[tuple[BronzeRecord, str | None]]:
        """Perform primary fetch and yield records with accession."""
        async for record in self.fetch_filtered(
            entity_type=entity_type,
            filter_ids=filter_ids,
            filter_field=filter_field,
            limit=limit,
        ):
            yield record, record.get("accession")

    def _should_do_fallback(
        self,
        filter_ids: list[str],
        found_ids: set[str],
        fallback_mapping: dict[str, str],
    ) -> list[str]:
        """Resolve missing IDs that qualify for fallback search.

        Returns:
            List of IDs that were not found in primary fetch and have a fallback mapping entry.
        """
        return resolve_uniprot_missing_ids(
            filter_ids=filter_ids,
            found_ids=found_ids,
            fallback_mapping=fallback_mapping,
        )

    async def fetch_filtered_with_fallback(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        fallback_mapping: dict[str, str],
        limit: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch records with primary lookup and fallback search."""
        if not filter_ids:
            return

        requested_ids = deduplicate_preserving_order(filter_ids)
        fallback_handler = UniProtFallbackPolicy(
            entity_type=entity_type,
            resolve_missing_ids=self._should_do_fallback,
            search_fallback=self._do_fallback_search,
        )

        async def _primary_records(
            primary_ids: list[str], request_limit: int | None
        ) -> AsyncIterator[BronzeRecord]:
            async for record, _ in self._do_primary_fetch(
                entity_type,
                primary_ids,
                filter_field,
                request_limit,
            ):
                yield record

        def _extract_accession(record: BronzeRecord) -> str | None:
            accession = record.get("accession")
            if not isinstance(accession, str):
                return None
            normalized = accession.strip()
            return normalized if normalized else None

        async for record in self._fallback_decorator.execute(
            filter_ids=requested_ids,
            fallback_mapping=fallback_mapping,
            primary_record_fetcher=_primary_records,
            limit=limit,
            filter_field=filter_field,
            extract_record_id=_extract_accession,
            fallback_handler=fallback_handler,
        ):
            yield record
