"""Extraction helpers for PublicationTermDataSource."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bioetl.application.core.entity_id import compute_publication_term_entity_id
from bioetl.domain.types import BronzeRecord

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from bioetl.domain.ports import FilterableDataSourcePort


class PublicationTermExtractionMixin:
    """Shared publication->term extraction flow."""

    async def _fetch_publication_terms(
        self: Any,  # Any: mixin self type is provided structurally by composed adapter class
        limit: int | None,
        filter_ids: list[str] | None,
        filter_field: str | None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch publications from wrapped source and yield extracted terms."""
        term_count = 0
        publication_limit = limit * self.PUBLICATION_LIMIT_MULTIPLIER if limit else None

        async for publication in self._data_source.fetch(
            entity_type=self.SOURCE_ENTITY_TYPE,
            limit=publication_limit,
            filter_ids=filter_ids,
            filter_field=filter_field,
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

    def _extract_terms_from_publication(
        self: Any,  # Any: mixin self type is provided structurally by composed adapter class
        record: BronzeRecord,
        publication_id: str,
    ) -> list[BronzeRecord]:
        """Extract and flatten all terms from a publication record."""
        terms: list[BronzeRecord] = []

        raw_mesh_terms = record.get("mesh_terms")
        mesh_terms: list[Any] = (  # Any: dynamic payload or structural mixin boundary
            raw_mesh_terms if isinstance(raw_mesh_terms, list) else []
        )
        for mesh in mesh_terms:
            if not isinstance(mesh, dict):
                continue

            mesh_heading = mesh.get("mesh_heading")
            if mesh_heading:
                terms.append(
                    self._create_term_record(
                        publication_id=publication_id,
                        term=mesh_heading,
                        term_type="MESH_HEADING",
                        mesh_id=mesh.get("mesh_id"),
                        qualifier=mesh.get("mesh_qualifier"),
                    )
                )

            mesh_qualifier = mesh.get("mesh_qualifier")
            if mesh_qualifier:
                terms.append(
                    self._create_term_record(
                        publication_id=publication_id,
                        term=mesh_qualifier,
                        term_type="MESH_QUALIFIER",
                        mesh_id=mesh.get("mesh_id"),
                        qualifier=None,
                    )
                )

        raw_keywords = record.get("keywords")
        keywords: list[Any] = (  # Any: dynamic payload or structural mixin boundary
            raw_keywords if isinstance(raw_keywords, list) else []
        )  # Any: dynamic payload or structural mixin boundary
        for keyword in keywords:
            if isinstance(keyword, str):
                stripped = keyword.strip()
                if stripped:
                    terms.append(
                        self._create_term_record(
                            publication_id=publication_id,
                            term=stripped,
                            term_type="KEYWORD",
                            mesh_id=None,
                            qualifier=None,
                        )
                    )

        return terms

    def _create_term_record(
        self: Any,  # Any: mixin self type is provided structurally by composed adapter class
        publication_id: str,
        term: str,
        term_type: str,
        mesh_id: str | None,
        qualifier: str | None,
    ) -> BronzeRecord:
        """Create a single publication-term record."""
        normalized_term = term.strip() if term else term
        entity_id = self._compute_entity_id(
            publication_id, term_type, normalized_term or ""
        )
        return {
            "entity_id": entity_id,
            "publication_id": publication_id,
            "term": normalized_term,
            "term_type": term_type,
            "mesh_id": mesh_id,
            "qualifier": qualifier,
        }

    def _compute_entity_id(
        self: Any,  # Any: mixin self type is provided structurally by composed adapter class
        publication_id: str,
        term_type: str,
        term: str,
    ) -> str:
        """Compute deterministic term entity ID."""
        return compute_publication_term_entity_id(publication_id, term_type, term)

    async def _fetch_filtered_publication_terms(
        self: Any,  # Any: mixin self type is provided structurally by composed adapter class
        filterable: FilterableDataSourcePort,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch filtered publications and yield extracted terms."""
        term_count = 0
        publication_limit = limit * self.PUBLICATION_LIMIT_MULTIPLIER if limit else None

        async for publication in filterable.fetch_filtered(
            entity_type=self.SOURCE_ENTITY_TYPE,
            filter_ids=filter_ids,
            filter_field=filter_field,
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
