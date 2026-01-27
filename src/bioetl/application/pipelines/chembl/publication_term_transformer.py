"""ChEMBL Publication Term Transformer.

Transforms Publication records to extract and flatten associated terms.
This is a derived entity transformer - it extracts nested term data
from Publication (ChEMBL Document) API responses and flattens the 1:M relationship.

Uses declarative field_specs DSL for mapping.

.. versionchanged:: 2.0.0
    Renamed from document_term_transformer to publication_term_transformer (ADR-024).
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any, cast

from bioetl.application.pipelines.chembl.base_chembl_transformer import (
    BaseChemblTransformer,
)
from bioetl.domain.entities import DocumentTerm

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.types import BronzeRecord, SilverRecord


class PublicationTermTransformer(BaseChemblTransformer):
    """Transforms ChEMBL publication records to extract flattened term records.

    This transformer extracts nested term data from Publication (ChEMBL Document)
    API responses and flattens the 1:M relationship (one Publication → multiple Terms).

    Term types extracted:
    - MESH_HEADING: MeSH descriptor terms from mesh_terms array
    - MESH_QUALIFIER: MeSH qualifiers/subheadings from mesh_terms
    - KEYWORD: Author-provided keywords from keywords array

    Entity ID is computed as SHA256 hash of composite key:
    (document_chembl_id, term_type, normalized_term)

    Note: This transformer returns multiple records from a single Publication,
    unlike standard transformers that have 1:1 input/output mapping.

    .. versionchanged:: 2.0.0
        Renamed from DocumentTermTransformer (ADR-024).
    """

    entity_class = DocumentTerm
    primary_id_field = "document_chembl_id"

    async def _transform_impl(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> SilverRecord | None:
        """Override base implementation to use composite entity_id.

        PublicationTerm is a derived entity with composite primary key:
        (document_chembl_id, term_type, term). The entity_id must be computed
        from all three fields, not just document_chembl_id.

        If record contains pre-computed entity_id (from PublicationTermDataSource),
        use it directly. Otherwise, compute composite entity_id.

        Args:
            context: Pipeline context with run_id, run_type, logger.
            record: Bronze record (pre-extracted term or raw publication).
            index: Sequential index of the record in the pipeline run.

        Returns:
            SilverRecord if transformation successful, None if skipped.

        """
        # 1. Validate primary ID (document_chembl_id)
        primary_id = self._get_required_field(record, self.primary_id_field)

        # 2. Extract business data (term details)
        business_data = self._extract_business_data(record, primary_id)

        # 3. Compute entity_id using composite key
        # Priority: pre-computed entity_id from record > computed from composite key
        pre_computed_id = record.get("entity_id")
        if pre_computed_id:
            entity_id = str(pre_computed_id)
        else:
            # Compute from composite key (document_chembl_id, term_type, term)
            entity_id = self.compute_term_entity_id(
                document_chembl_id=str(
                    business_data.get("document_chembl_id", primary_id)
                ),
                term_type=str(business_data.get("term_type", "")),
                term=str(business_data.get("term", "")),
            )

        # 4. Compute content hash
        content_hash = self.compute_content_hash(business_data, exclude_none=True)

        # 5. Create domain entity
        entity = self._create_entity(
            self.entity_class,
            context,
            entity_id=entity_id,
            content_hash=content_hash,
            index=index,
            **business_data,
        )

        # 6. Convert to SilverRecord
        return cast("SilverRecord", self.entity_to_silver_record(entity))

    def _extract_business_data(
        self,
        record: BronzeRecord,
        primary_id: Any,
    ) -> dict[str, Any]:
        """Extract term data from the record.

        Handles two cases:
        1. Pre-extracted term records (from PublicationTermDataSource) - pass through
        2. Raw publication records - extract terms from mesh_terms/keywords arrays

        Args:
            record: Bronze record (either term record or document record).
            primary_id: Validated document_chembl_id value.

        Returns:
            Dictionary of term business fields.

        """
        # Case 1: Record is already a term record (from PublicationTermDataSource)
        # These records have 'term' and 'term_type' fields directly
        if "term" in record and "term_type" in record:
            return {
                "document_chembl_id": str(record.get("document_chembl_id", primary_id)),
                "term": record.get("term", ""),
                "term_type": record.get("term_type", ""),
                "mesh_id": record.get("mesh_id"),
                "qualifier": record.get("qualifier"),
            }

        # Case 2: Raw document record - extract terms from nested arrays
        terms = list(self.extract_terms_from_document(record, str(primary_id)))
        if not terms:
            # Return empty data that will fail validation
            return {
                "document_chembl_id": str(primary_id),
                "term": "",
                "term_type": "",
                "mesh_id": None,
                "qualifier": None,
            }
        return terms[0]

    def extract_terms_from_document(
        self,
        record: BronzeRecord,
        document_chembl_id: str,
    ) -> list[dict[str, Any]]:
        """Extract and flatten all terms from a Publication record.

        Yields multiple term records from one publication.
        This is the primary method for derived entity extraction.

        Args:
            record: Raw Bronze record from ChEMBL API.
            document_chembl_id: Document ChEMBL ID.

        Yields:
            Dictionary of term business fields for each term.

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
                    self._create_term_data(
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
                    self._create_term_data(
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
                if stripped:  # Skip empty strings after stripping
                    terms.append(
                        self._create_term_data(
                            document_chembl_id=document_chembl_id,
                            term=stripped,
                            term_type="KEYWORD",
                            mesh_id=None,
                            qualifier=None,
                        )
                    )

        return terms

    def _create_term_data(
        self,
        document_chembl_id: str,
        term: str,
        term_type: str,
        mesh_id: str | None,
        qualifier: str | None,
    ) -> dict[str, Any]:
        """Create a single term data dictionary.

        Args:
            document_chembl_id: Parent document ChEMBL ID.
            term: Term text.
            term_type: Term type (MESH_HEADING, MESH_QUALIFIER, KEYWORD, CONCEPT).
            mesh_id: MeSH identifier if applicable.
            qualifier: MeSH qualifier if applicable.

        Returns:
            Dictionary of term business fields.

        """
        return {
            "document_chembl_id": document_chembl_id,
            "term": term.strip() if term else term,
            "term_type": term_type,
            "mesh_id": mesh_id,
            "qualifier": qualifier,
        }

    def compute_term_entity_id(
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
