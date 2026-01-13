"""Publication Term Data Source wrapper.

Wraps a DataSourcePort to extract terms from ChEMBL publication records.
This is a derived entity pattern - publication_term entities are extracted
from the nested mesh_terms and keywords fields in publication records.

Architecture:
    ChEMBL API (document endpoint)
           ↓
    PublicationTermDataSource (wrapper)
      - fetch("document_term") → wrapped.fetch("document")
      - transforms each publication → yields term records
           ↓
    Pipeline receives term records

.. versionchanged:: 2.0.0
    Renamed from DocumentTermDataSource to PublicationTermDataSource (ADR-024).
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any, Self

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from bioetl.domain.ports import DataSourcePort
    from bioetl.domain.types import HealthStatus


class PublicationTermDataSource:
    """Wraps a DataSourcePort to extract terms from publication records.

    This is a Decorator pattern implementation that transforms the publication
    entity into derived publication_term entities. For each publication fetched
    from the wrapped adapter, multiple term records are extracted and yielded.

    Term types extracted:
    - MESH_HEADING: MeSH descriptor terms from mesh_terms array
    - MESH_QUALIFIER: MeSH qualifiers/subheadings from mesh_terms
    - KEYWORD: Author-provided keywords from keywords array

    The wrapper:
    1. Intercepts fetch("document_term") calls
    2. Fetches publications from the wrapped adapter via fetch("document")
    3. Extracts terms from each publication (1:M relationship)
    4. Yields individual term records with computed entity_id
    5. Delegates all other operations to the wrapped adapter

    Example:
        >>> wrapped = PublicationTermDataSource(chembl_adapter)
        >>> async with wrapped:
        ...     async for term in wrapped.fetch("document_term", limit=100):
        ...         process_term(term)  # term has keys: term, term_type, etc.

    .. versionchanged:: 2.0.0
        Renamed from DocumentTermDataSource (ADR-024).
    """

    # Source entity type to fetch from wrapped adapter
    SOURCE_ENTITY_TYPE = "document"
    # Target entity type this wrapper provides
    TARGET_ENTITY_TYPE = "document_term"
    # Multiplier for publication limit estimation.
    # Not all publications have terms (mesh_terms/keywords may be empty).
    # Analysis shows ~20-30% of ChEMBL publications have terms.
    # Using 50x multiplier ensures we fetch enough publications to satisfy term limit.
    PUBLICATION_LIMIT_MULTIPLIER = 50

    def __init__(
        self,
        data_source: DataSourcePort,
    ) -> None:
        """Initialize publication term data source wrapper.

        Args:
            data_source: The underlying data source adapter to wrap (ChemblAdapter).

        """
        self._data_source = data_source

    @property
    def provider_name(self) -> str:
        """Provider name from the wrapped data source."""
        return self._data_source.provider_name

    async def __aenter__(self) -> Self:
        """Enter async context."""
        await self._data_source.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit async context."""
        await self._data_source.__aexit__(exc_type, exc_val, exc_tb)

    async def fetch(
        self,
        entity_type: str,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch records, extracting terms if entity_type is document_term.

        For document_term entity type:
        - Fetches documents from wrapped adapter
        - Extracts terms from each document
        - Yields individual term records

        For other entity types:
        - Delegates directly to wrapped adapter

        Args:
            entity_type: Type of entity to fetch.
            limit: Maximum number of records (for document_term, limits total terms).
            query: Optional search query.
            filter_ids: Optional filter IDs (passed to wrapped adapter).
            filter_field: Optional filter field (passed to wrapped adapter).

        Yields:
            Records from the data source.

        """
        if entity_type == self.TARGET_ENTITY_TYPE:
            # Fetch publications and extract terms
            async for term in self._fetch_publication_terms(
                limit, filter_ids, filter_field
            ):
                yield term
        else:
            # Delegate to wrapped adapter for other entity types
            async for record in self._data_source.fetch(
                entity_type=entity_type,
                limit=limit,
                query=query,
                filter_ids=filter_ids,
                filter_field=filter_field,
            ):
                yield record

    async def _fetch_publication_terms(
        self,
        limit: int | None,
        filter_ids: list[str] | None,
        filter_field: str | None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch publications and extract terms.

        Args:
            limit: Maximum number of term records to yield.
            filter_ids: Optional publication IDs to filter by.
            filter_field: Optional field for filtering (typically document_chembl_id).

        Yields:
            Term records extracted from publications.

        """
        term_count = 0

        # Estimate publication limit based on term limit.
        # We need to fetch more publications than terms because:
        # 1. Not all publications have terms (mesh_terms/keywords may be empty)
        # 2. Each publication yields variable number of terms (~2-5 on average)
        # Using multiplier ensures we fetch enough publications to satisfy term limit.
        publication_limit = limit * self.PUBLICATION_LIMIT_MULTIPLIER if limit else None

        async for publication in self._data_source.fetch(
            entity_type=self.SOURCE_ENTITY_TYPE,
            limit=publication_limit,
            filter_ids=filter_ids,
            filter_field=filter_field,
        ):
            document_chembl_id = publication.get("document_chembl_id")
            if not document_chembl_id:
                continue

            # Extract terms from publication
            terms = self._extract_terms_from_publication(
                publication, document_chembl_id
            )

            for term in terms:
                yield term
                term_count += 1

                if limit and term_count >= limit:
                    return

    def _extract_terms_from_publication(
        self,
        record: dict[str, Any],
        document_chembl_id: str,
    ) -> list[dict[str, Any]]:
        """Extract and flatten all terms from a Publication record.

        Extracts multiple term records from one publication (1:M relationship).

        Args:
            record: Raw publication record from ChEMBL API.
            document_chembl_id: Publication ChEMBL ID.

        Returns:
            List of term dictionaries.

        """
        terms: list[dict[str, Any]] = []

        # Extract MeSH terms
        raw_mesh_terms = record.get("mesh_terms")
        mesh_terms: list[Any] = (
            raw_mesh_terms if isinstance(raw_mesh_terms, list) else []
        )
        for mesh in mesh_terms:
            if not isinstance(mesh, dict):
                continue

            mesh_heading = mesh.get("mesh_heading")
            if mesh_heading:
                terms.append(
                    self._create_term_record(
                        document_chembl_id=document_chembl_id,
                        term=mesh_heading,
                        term_type="MESH_HEADING",
                        mesh_id=mesh.get("mesh_id"),
                        qualifier=mesh.get("mesh_qualifier"),
                    )
                )

            # Extract qualifier as separate term if present
            mesh_qualifier = mesh.get("mesh_qualifier")
            if mesh_qualifier:
                terms.append(
                    self._create_term_record(
                        document_chembl_id=document_chembl_id,
                        term=mesh_qualifier,
                        term_type="MESH_QUALIFIER",
                        mesh_id=mesh.get("mesh_id"),
                        qualifier=None,
                    )
                )

        # Extract keywords
        raw_keywords = record.get("keywords")
        keywords: list[Any] = raw_keywords if isinstance(raw_keywords, list) else []
        for keyword in keywords:
            if isinstance(keyword, str):
                stripped = keyword.strip()
                if stripped:  # Skip empty strings
                    terms.append(
                        self._create_term_record(
                            document_chembl_id=document_chembl_id,
                            term=stripped,
                            term_type="KEYWORD",
                            mesh_id=None,
                            qualifier=None,
                        )
                    )

        return terms

    def _create_term_record(
        self,
        document_chembl_id: str,
        term: str,
        term_type: str,
        mesh_id: str | None,
        qualifier: str | None,
    ) -> dict[str, Any]:
        """Create a single term record dictionary.

        Computes entity_id as SHA256 hash of composite key for deduplication.

        Args:
            document_chembl_id: Parent document ChEMBL ID.
            term: Term text.
            term_type: Term type (MESH_HEADING, MESH_QUALIFIER, KEYWORD).
            mesh_id: MeSH identifier if applicable.
            qualifier: MeSH qualifier if applicable.

        Returns:
            Dictionary of term fields including computed entity_id.

        """
        # Compute entity_id from composite key
        entity_id = self._compute_entity_id(document_chembl_id, term_type, term)

        return {
            "entity_id": entity_id,
            "document_chembl_id": document_chembl_id,
            "term": term.strip() if term else term,
            "term_type": term_type,
            "mesh_id": mesh_id,
            "qualifier": qualifier,
        }

    def _compute_entity_id(
        self,
        document_chembl_id: str,
        term_type: str,
        term: str,
    ) -> str:
        """Compute entity ID for a term based on composite key.

        Entity ID is SHA256 hash of: document_chembl_id:term_type:normalized_term

        Args:
            document_chembl_id: Document ChEMBL ID.
            term_type: Term type classification.
            term: Term text (will be normalized).

        Returns:
            Entity ID string (first 16 chars of SHA256 hex digest).

        """
        normalized_term = term.lower().strip() if term else ""
        composite = f"{document_chembl_id}:{term_type}:{normalized_term}"
        return hashlib.sha256(composite.encode()).hexdigest()[:16]

    async def health_check(self) -> HealthStatus:
        """Delegate health check to wrapped adapter."""
        return await self._data_source.health_check()

    async def aclose(self) -> None:
        """Delegate close to wrapped adapter."""
        await self._data_source.aclose()


# Backward-compatible alias (deprecated, ADR-024)
DocumentTermDataSource = PublicationTermDataSource
