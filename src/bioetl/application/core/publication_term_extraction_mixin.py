"""Extraction helpers for PublicationTermDataSource."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bioetl.application.core.publication_term_runtime import (
    compute_term_entity_id,
    create_term_record,
    extract_terms_from_publication,
)
from bioetl.domain.types import BronzeRecord

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from bioetl.domain.ports import FilterableDataSourcePort


class PublicationTermExtractionMixin:
    """Shared publication->term extraction flow."""
    async def _yield_terms_from_publications(
        self: Any,  # Any: mixin self type is provided structurally by composed adapter class
        publications: AsyncIterator[BronzeRecord],
        limit: int | None,
    ) -> AsyncIterator[BronzeRecord]:
        """Expand a publication stream into term records with optional limit."""
        term_count = 0
        try:
            async for publication in publications:
                publication_id = publication.get("publication_id") or publication.get(
                    "document_chembl_id"
                )
                if not publication_id:
                    continue
                terms = self._extract_terms_from_publication(
                    publication, publication_id
                )
                for term in terms:
                    yield term
                    term_count += 1
                    if limit and term_count >= limit:
                        return
        finally:
            aclose = getattr(publications, "aclose", None)
            if callable(aclose):
                from collections.abc import Awaitable, Callable
                from typing import cast
                aclose_fn = cast(Callable[[], Awaitable[object]], aclose)
                await aclose_fn()
    async def _fetch_publication_terms(
        self: Any,  # Any: mixin self type is provided structurally by composed adapter class
        limit: int | None,
        filter_ids: list[str] | None,
        filter_field: str | None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch publications from wrapped source and yield extracted terms.
        Args:
            limit: Optional maximum number of term records to yield. The upstream
                publication fetch uses a multiplied limit to account for term expansion.
            filter_ids: Optional list of identifier values to pass to the upstream fetch.
                When None, no ID filter is applied.
            filter_field: Optional field name on which to filter upstream publications.
                When None, no field filter is applied.
        """
        publication_limit = limit * self.PUBLICATION_LIMIT_MULTIPLIER if limit else None
        publications = self._data_source.fetch(
            entity_type=self.SOURCE_ENTITY_TYPE,
            limit=publication_limit,
            filter_ids=filter_ids,
            filter_field=filter_field,
        )
        async for term in self._yield_terms_from_publications(publications, limit):
            yield term
    def _extract_terms_from_publication(
        self: Any,  # Any: mixin self type is provided structurally by composed adapter class
        record: BronzeRecord,
        publication_id: str,
    ) -> list[BronzeRecord]:
        """Extract and flatten all terms from a publication record.
        Args:
            record: Raw Bronze publication record containing ``mesh_terms`` and ``keywords`` fields.
            publication_id: Identifier of the parent publication used to link each term record.
        Returns:
            List of Bronze term records, one per MeSH heading, MeSH qualifier, or keyword found.
        """
        return extract_terms_from_publication(record, publication_id)
    def _create_term_record(
        self: Any,  # Any: mixin self type is provided structurally by composed adapter class
        publication_id: str,
        term: str,
        term_type: str,
        mesh_id: str | None,
        qualifier: str | None,
    ) -> BronzeRecord:
        """Create a single publication-term record.
        Args:
            publication_id: Identifier of the parent publication.
            term: Text of the extracted term, stripped of surrounding whitespace.
            term_type: Controlled vocabulary type (e.g., ``'MESH_HEADING'``, ``'KEYWORD'``).
            mesh_id: Optional MeSH concept identifier associated with the term.
            qualifier: Optional MeSH qualifier string. Pass None for non-qualified terms.
        Returns:
            Bronze record dict with ``entity_id``, ``publication_id``, ``term``,
            ``term_type``, ``mesh_id``, and ``qualifier`` fields.
        """
        return create_term_record(
            publication_id=publication_id,
            term=term,
            term_type=term_type,
            mesh_id=mesh_id,
            qualifier=qualifier,
        )
    def _compute_entity_id(
        self: Any,  # Any: mixin self type is provided structurally by composed adapter class
        publication_id: str,
        term_type: str,
        term: str,
    ) -> str:
        """Compute deterministic term entity ID.
        Args:
            publication_id: Identifier of the parent publication.
            term_type: Controlled vocabulary type (e.g., ``'MESH_HEADING'``).
            term: Normalized term text used as part of the hash input.
        Returns:
            Deterministic string entity ID derived from the composite key.
        """
        return compute_term_entity_id(
            publication_id=publication_id,
            term_type=term_type,
            term=term,
        )
    async def _fetch_filtered_publication_terms(
        self: Any,  # Any: mixin self type is provided structurally by composed adapter class
        filterable: FilterableDataSourcePort,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch filtered publications and yield extracted terms.
        Args:
            filterable: Filterable data source port to delegate publication fetching to.
            filter_ids: List of identifier values to filter upstream publications by.
            filter_field: Field name on which to apply the filter.
            limit: Optional maximum number of term records to yield. The upstream
                publication fetch uses a multiplied limit to account for term expansion.
        """
        publication_limit = limit * self.PUBLICATION_LIMIT_MULTIPLIER if limit else None
        publications = filterable.fetch_filtered(
            entity_type=self.SOURCE_ENTITY_TYPE,
            filter_ids=filter_ids,
            filter_field=filter_field,
            limit=publication_limit,
        )
        async for term in self._yield_terms_from_publications(publications, limit):
            yield term
