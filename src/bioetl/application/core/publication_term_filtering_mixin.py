"""Filterable delegation helpers for PublicationTermDataSource."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bioetl.application.core._data_source_mixins import (
    _FilterableTargetDelegationMixin,
)
from bioetl.domain.ports import FilterableDataSourcePort
from bioetl.domain.types import BronzeRecord

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


class PublicationTermFilteringMixin(_FilterableTargetDelegationMixin):
    """FilterableDataSourcePort-compatible delegation for term extraction wrapper."""

    async def _fetch_target_filtered_records(
        self: Any,  # Any: mixin self type is provided structurally by composed adapter class
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
        self: Any,  # Any: mixin self type is provided structurally by composed adapter class
        filterable: FilterableDataSourcePort,
        filters: dict[str, list[str]],
        limit: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Yield publication-term records from multi-filtered upstream publications."""
        publication_limit = limit * self.PUBLICATION_LIMIT_MULTIPLIER if limit else None
        async for record in self._yield_terms_from_publications(
            filterable.fetch_multi_filtered(
                entity_type=self.SOURCE_ENTITY_TYPE,
                filters=filters,
                limit=publication_limit,
            ),
            limit,
        ):
            yield record

    async def _fetch_target_filtered_with_fallback_records(
        self: Any,  # Any: mixin self type is provided structurally by composed adapter class
        filterable: FilterableDataSourcePort,
        filter_ids: list[str],
        filter_field: str,
        fallback_mapping: dict[str, str],
        limit: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Yield publication-term records from fallback-enabled publications."""
        publication_limit = limit * self.PUBLICATION_LIMIT_MULTIPLIER if limit else None
        async for record in self._yield_terms_from_publications(
            filterable.fetch_filtered_with_fallback(
                entity_type=self.SOURCE_ENTITY_TYPE,
                filter_ids=filter_ids,
                filter_field=filter_field,
                fallback_mapping=fallback_mapping,
                limit=publication_limit,
            ),
            limit,
        ):
            yield record
