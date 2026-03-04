"""Filterable delegation helpers for PublicationTermDataSource."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bioetl.domain.ports import FilterableDataSourcePort
from bioetl.domain.types import BronzeRecord

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


class PublicationTermFilteringMixin:
    """FilterableDataSourcePort-compatible delegation for term extraction wrapper."""

    def _ensure_filterable(
        self: Any,  # Any: mixin self type is provided structurally by composed adapter class
        method_name: str,  # Any: mixin self type is provided structurally by composed adapter class
    ) -> (
        FilterableDataSourcePort
    ):  # Any: mixin self type is provided structurally by composed adapter class
        """Validate wrapped source implements FilterableDataSourcePort."""
        if not isinstance(self._data_source, FilterableDataSourcePort):
            raise TypeError(
                f"Wrapped adapter {self._data_source.provider_name} does not implement "
                f"FilterableDataSourcePort. {method_name}() requires a filterable adapter."
            )
        return self._data_source

    async def fetch_filtered(
        self: Any,  # Any: mixin self type is provided structurally by composed adapter class
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch filtered records, extracting terms for publication_term target."""
        filterable = self._ensure_filterable("fetch_filtered")

        if entity_type == self.TARGET_ENTITY_TYPE:
            async for term in self._fetch_filtered_publication_terms(
                filterable, filter_ids, filter_field, limit
            ):
                yield term
            return

        async for record in filterable.fetch_filtered(
            entity_type=entity_type,
            filter_ids=filter_ids,
            filter_field=filter_field,
            limit=limit,
        ):
            yield record

    async def fetch_multi_filtered(
        self: Any,  # Any: mixin self type is provided structurally by composed adapter class
        entity_type: str,
        filters: dict[str, list[str]],
        limit: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch multi-filtered records with publication-term extraction support."""
        filterable = self._ensure_filterable("fetch_multi_filtered")

        if entity_type != self.TARGET_ENTITY_TYPE:
            async for record in filterable.fetch_multi_filtered(
                entity_type=entity_type,
                filters=filters,
                limit=limit,
            ):
                yield record
            return

        term_count = 0
        publication_limit = limit * self.PUBLICATION_LIMIT_MULTIPLIER if limit else None
        async for publication in filterable.fetch_multi_filtered(
            entity_type=self.SOURCE_ENTITY_TYPE,
            filters=filters,
            limit=publication_limit,
        ):
            publication_id = publication.get("publication_id") or publication.get(
                "document_chembl_id"
            )
            if not publication_id:
                continue

            terms = self._extract_terms_from_publication(publication, publication_id)
            for term in terms:
                yield term
                term_count += 1
                if limit and term_count >= limit:
                    return

    async def fetch_filtered_with_fallback(
        self: Any,  # Any: mixin self type is provided structurally by composed adapter class
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        fallback_mapping: dict[str, str],
        limit: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch with fallback and publication-term extraction support."""
        filterable = self._ensure_filterable("fetch_filtered_with_fallback")

        if entity_type != self.TARGET_ENTITY_TYPE:
            async for record in filterable.fetch_filtered_with_fallback(
                entity_type=entity_type,
                filter_ids=filter_ids,
                filter_field=filter_field,
                fallback_mapping=fallback_mapping,
                limit=limit,
            ):
                yield record
            return

        term_count = 0
        publication_limit = limit * self.PUBLICATION_LIMIT_MULTIPLIER if limit else None
        async for publication in filterable.fetch_filtered_with_fallback(
            entity_type=self.SOURCE_ENTITY_TYPE,
            filter_ids=filter_ids,
            filter_field=filter_field,
            fallback_mapping=fallback_mapping,
            limit=publication_limit,
        ):
            publication_id = publication.get("publication_id") or publication.get(
                "document_chembl_id"
            )
            if not publication_id:
                continue

            terms = self._extract_terms_from_publication(publication, publication_id)
            for term in terms:
                yield term
                term_count += 1
                if limit and term_count >= limit:
                    return
