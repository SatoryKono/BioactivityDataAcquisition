"""Publication Term Data Source wrapper.

Wraps a DataSourcePort to extract terms from ChEMBL publication records.
This is a derived entity pattern - publication_term entities are extracted
from the nested mesh_terms and keywords fields in publication records.

Architecture:
    ChEMBL API (document endpoint)
           ↓
    PublicationTermDataSource (wrapper)
      - fetch("publication_term") → wrapped.fetch("publication")
      - transforms each publication → yields term records
           ↓
    Pipeline receives term records

.. versionchanged:: 2.0.0
    Renamed from DocumentTermDataSource to PublicationTermDataSource (ADR-024).
.. versionchanged:: 2.1.0
    Changed entity types from document/document_term to publication/publication_term
    for naming consistency (ADR-024 naming unification).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self

from bioetl.application.core._data_source_mixins import _SourceMetadataDelegationMixin
from bioetl.application.core.entity_id import compute_publication_term_entity_id
from bioetl.domain.ports import FilterableDataSourcePort

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from bioetl.domain.ports import DataSourcePort
    from bioetl.domain.types import HealthStatus


class PublicationTermDataSource(_SourceMetadataDelegationMixin):
    """Wraps a DataSourcePort to extract terms from publication records.

    This is a Decorator pattern implementation that transforms the publication
    entity into derived publication_term entities. For each publication fetched
    from the wrapped adapter, multiple term records are extracted and yielded.

    Term types extracted:
    - MESH_HEADING: MeSH descriptor terms from mesh_terms array
    - MESH_QUALIFIER: MeSH qualifiers/subheadings from mesh_terms
    - KEYWORD: Author-provided keywords from keywords array

    The wrapper:
    1. Intercepts fetch("publication_term") calls
    2. Fetches publications from the wrapped adapter via fetch("publication")
    3. Extracts terms from each publication (1:M relationship)
    4. Yields individual term records with computed entity_id
    5. Delegates all other operations to the wrapped adapter

    Example:
        >>> wrapped = PublicationTermDataSource(chembl_adapter)
        >>> async with wrapped:
        ...     async for term in wrapped.fetch("publication_term", limit=100):
        ...         process_term(term)  # term has keys: term, term_type, etc.

    .. versionchanged:: 2.0.0
        Renamed from DocumentTermDataSource (ADR-024).
    """

    # Source entity type to fetch from wrapped adapter
    # Uses canonical "publication" name (ADR-024 naming unification)
    SOURCE_ENTITY_TYPE = "publication"
    # Target entity type this wrapper provides
    # Uses canonical "publication_term" name (ADR-024 naming unification)
    TARGET_ENTITY_TYPE = "publication_term"
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
        exc_tb: Any,  # Any: TracebackType | None per async context manager protocol
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
        offset: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch records, extracting terms if entity_type is publication_term.

        For publication_term entity type:
        - Fetches publications from wrapped adapter
        - Extracts terms from each publication
        - Yields individual term records

        For other entity types:
        - Delegates directly to wrapped adapter

        Args:
            entity_type: Type of entity to fetch.
            limit: Maximum number of records (for publication_term, limits total terms).
            query: Optional search query.
            filter_ids: Optional filter IDs (passed to wrapped adapter).
            filter_field: Optional filter field (passed to wrapped adapter).
            offset: Optional starting offset for checkpoint-based resume.

        Yields:
            Records from the data source.

        Returns:
            Async iterator yielding fetched records.
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
                offset=offset,
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
            filter_field: Optional field for filtering (typically publication_id).

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
            publication_id = publication.get("publication_id") or publication.get(
                "document_chembl_id"
            )
            if not publication_id:
                continue

            # Extract terms from publication
            terms = self._extract_terms_from_publication(publication, publication_id)

            for term in terms:
                yield term
                term_count += 1

                if limit and term_count >= limit:
                    return

    def _extract_terms_from_publication(
        self,
        record: dict[str, Any],
        publication_id: str,
    ) -> list[dict[str, Any]]:
        """Extract and flatten all terms from a Publication record.

        Extracts multiple term records from one publication (1:M relationship).

        Args:
            record: Raw publication record from ChEMBL API.
            publication_id: Publication ID.

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
                        publication_id=publication_id,
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
                        publication_id=publication_id,
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
                            publication_id=publication_id,
                            term=stripped,
                            term_type="KEYWORD",
                            mesh_id=None,
                            qualifier=None,
                        )
                    )

        return terms

    def _create_term_record(
        self,
        publication_id: str,
        term: str,
        term_type: str,
        mesh_id: str | None,
        qualifier: str | None,
    ) -> dict[str, Any]:
        """Create a single term record dictionary.

        Computes entity_id as SHA256 hash of composite key for deduplication.

        Args:
            publication_id: Parent publication ID.
            term: Term text.
            term_type: Term type (MESH_HEADING, MESH_QUALIFIER, KEYWORD).
            mesh_id: MeSH identifier if applicable.
            qualifier: MeSH qualifier if applicable.

        Returns:
            Dictionary of term fields including computed entity_id.

        """
        # Compute entity_id from composite key
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
        self,
        publication_id: str,
        term_type: str,
        term: str,
    ) -> str:
        """Compute entity ID for a term based on composite key.

        Delegates to shared ``compute_publication_term_entity_id``.

        Args:
            publication_id: Publication ID.
            term_type: Term type classification.
            term: Term text (will be normalized).

        Returns:
            Entity ID string (first 16 chars of SHA256 hex digest).

        """
        return compute_publication_term_entity_id(publication_id, term_type, term)

    async def health_check(self) -> HealthStatus:
        """Delegate health check to wrapped adapter.

        Returns:
            The HealthStatus result.
        """
        return await self._data_source.health_check()

    async def aclose(self) -> None:
        """Delegate close to wrapped adapter."""
        await self._data_source.aclose()

    # FilterableDataSourcePort implementation (delegates to wrapped adapter)

    def _ensure_filterable(self, method_name: str) -> FilterableDataSourcePort:
        """Check that wrapped adapter implements FilterableDataSourcePort.

        Args:
            method_name: Name of the method being called (for error message).

        Returns:
            Wrapped adapter cast to FilterableDataSourcePort.

        Raises:
            TypeError: If wrapped adapter doesn't implement FilterableDataSourcePort.

        """
        if not isinstance(self._data_source, FilterableDataSourcePort):
            raise TypeError(
                f"Wrapped adapter {self._data_source.provider_name} does not implement "
                f"FilterableDataSourcePort. {method_name}() requires a filterable adapter."
            )
        return self._data_source

    async def fetch_filtered(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch filtered records, extracting terms if entity_type is publication_term.

        Implements FilterableDataSourcePort.fetch_filtered().

        For publication_term entity type:
        - Delegates to wrapped adapter's fetch_filtered("publication", ...)
        - Extracts terms from each publication

        For other entity types:
        - Delegates directly to wrapped adapter

        Args:
            entity_type: Type of entity to fetch.
            filter_ids: List of IDs to filter by (publication_id for publication_term).
            filter_field: Field name to filter on.
            limit: Maximum number of records to fetch.

        Yields:
            Dictionary records matching the filter criteria.

        Returns:
            Async iterator yielding fetched records.
        """
        filterable = self._ensure_filterable("fetch_filtered")

        if entity_type == self.TARGET_ENTITY_TYPE:
            # Fetch publications and extract terms
            async for term in self._fetch_filtered_publication_terms(
                filterable, filter_ids, filter_field, limit
            ):
                yield term
        else:
            # Delegate to wrapped adapter for other entity types
            async for record in filterable.fetch_filtered(
                entity_type=entity_type,
                filter_ids=filter_ids,
                filter_field=filter_field,
                limit=limit,
            ):
                yield record

    async def _fetch_filtered_publication_terms(
        self,
        filterable: FilterableDataSourcePort,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch filtered publications and extract terms.

        Args:
            filterable: Wrapped adapter that implements FilterableDataSourcePort.
            filter_ids: Publication IDs to filter by.
            filter_field: Field name (typically publication_id).
            limit: Maximum number of term records to yield.

        Yields:
            Term records extracted from filtered publications.

        """
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

    async def fetch_multi_filtered(
        self,
        entity_type: str,
        filters: dict[str, list[str]],
        limit: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch records filtered by multiple fields (AND logic).

        Implements FilterableDataSourcePort.fetch_multi_filtered().

        Args:
            entity_type: Type of entity to fetch.
            filters: Mapping from filter_field to list of IDs.
            limit: Maximum number of records to fetch.

        Yields:
            Dictionary records matching ALL filter criteria.

        Returns:
            Async iterator yielding fetched records.
        """
        filterable = self._ensure_filterable("fetch_multi_filtered")

        if entity_type == self.TARGET_ENTITY_TYPE:
            # Fetch publications and extract terms
            term_count = 0
            publication_limit = (
                limit * self.PUBLICATION_LIMIT_MULTIPLIER if limit else None
            )

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

                terms = self._extract_terms_from_publication(
                    publication, publication_id
                )

                for term in terms:
                    yield term
                    term_count += 1
                    if limit and term_count >= limit:
                        return
        else:
            # Delegate to wrapped adapter for other entity types
            async for record in filterable.fetch_multi_filtered(
                entity_type=entity_type,
                filters=filters,
                limit=limit,
            ):
                yield record

    async def fetch_filtered_with_fallback(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        fallback_mapping: dict[str, str],
        limit: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch records with fallback search when primary lookup fails.

        Implements FilterableDataSourcePort.fetch_filtered_with_fallback().

        Args:
            entity_type: Type of entity to fetch.
            filter_ids: List of primary IDs to filter by.
            filter_field: Field name for primary filtering.
            fallback_mapping: Mapping from primary ID to fallback value.
            limit: Maximum number of records to fetch.

        Yields:
            Dictionary records found via primary lookup or fallback search.

        Returns:
            Async iterator yielding fetched records.
        """
        filterable = self._ensure_filterable("fetch_filtered_with_fallback")

        if entity_type == self.TARGET_ENTITY_TYPE:
            # Fetch publications and extract terms
            term_count = 0
            publication_limit = (
                limit * self.PUBLICATION_LIMIT_MULTIPLIER if limit else None
            )

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

                terms = self._extract_terms_from_publication(
                    publication, publication_id
                )

                for term in terms:
                    yield term
                    term_count += 1
                    if limit and term_count >= limit:
                        return
        else:
            # Delegate to wrapped adapter for other entity types
            async for record in filterable.fetch_filtered_with_fallback(
                entity_type=entity_type,
                filter_ids=filter_ids,
                filter_field=filter_field,
                fallback_mapping=fallback_mapping,
                limit=limit,
            ):
                yield record
