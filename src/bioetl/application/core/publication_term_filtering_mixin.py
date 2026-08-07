"""Filterable delegation helpers for PublicationTermDataSource."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol, cast

from bioetl.application.core.publication_term_extraction_mixin import (
    PublicationTermExtractionHost,
    normalize_publication_term_limit,
)
from bioetl.application.core.target_data_source_mixins import (
    _FallbackFilterableTargetFetchMixin,
    _FilterableTargetDelegationMixin,
)
from bioetl.domain.ports import FilterableDataSourcePort
from bioetl.domain.types import BronzeRecord


class PublicationTermFilteringHost(PublicationTermExtractionHost, Protocol):
    """Host surface for filterable publication-term delegation."""

    def _fetch_filtered_publication_terms(
        self,
        filterable: FilterableDataSourcePort,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None,
    ) -> AsyncIterator[BronzeRecord]: ...


class PublicationTermFilteringMixin(
    _FallbackFilterableTargetFetchMixin,
    _FilterableTargetDelegationMixin,
):
    """FilterableDataSourcePort-compatible delegation for term extraction wrapper."""

    async def _fetch_target_filtered_records(
        self: PublicationTermFilteringHost,
        filterable: FilterableDataSourcePort,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Yield publication-term records from filtered upstream publications."""
        async for record in self._fetch_filtered_publication_terms(
            filterable, filter_ids, filter_field, limit
        ):
            yield record

    async def _fetch_target_multi_filtered_records(
        self: PublicationTermFilteringHost,
        filterable: FilterableDataSourcePort,
        filters: dict[str, list[str]],
        limit: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Yield publication-term records from multi-filtered upstream publications."""
        term_cap = normalize_publication_term_limit(limit)
        if term_cap == 0:
            return
        # Scale only when a positive finite term cap is requested.
        upstream_cap = (
            None if term_cap is None else term_cap * self.PUBLICATION_LIMIT_MULTIPLIER
        )
        async for record in self._yield_terms_from_publications(
            filterable.fetch_multi_filtered(
                entity_type=self.SOURCE_ENTITY_TYPE,
                filters=filters,
                limit=upstream_cap,
            ),
            term_cap,
        ):
            yield record

    def _resolve_target_fallback_upstream_limit(
        self: PublicationTermFilteringHost,
        limit: int | None = None,
    ) -> int | None:
        """Scale upstream publication fetches to account for term expansion.

        ``limit=0`` remains zero (no upstream fetch), rather than being treated
        as absent/unlimited via truthiness.
        """
        normalized_limit = normalize_publication_term_limit(limit)
        if normalized_limit is None:
            return None
        return normalized_limit * self.PUBLICATION_LIMIT_MULTIPLIER

    def _yield_target_records_from_fallback_source_records(
        self: PublicationTermFilteringHost,
        source_records: AsyncIterator[object],
        limit: int | None,
    ) -> AsyncIterator[BronzeRecord]:
        """Transform fallback-fetched publications into publication-term records."""
        return self._yield_terms_from_publications(
            cast("AsyncIterator[BronzeRecord]", source_records),
            limit,
        )
