"""ChEMBL Document Term Transformer.

Transforms Document records to extract and flatten associated terms.
This is a derived entity transformer - it extracts nested term data
from Document API responses and flattens the 1:M relationship.

Uses declarative field_specs DSL for mapping.
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any, ClassVar

from bioetl.application.pipelines.chembl.base_chembl_transformer import (
    BaseChemblTransformer,
)
from bioetl.domain.entities import DocumentTerm

if TYPE_CHECKING:
    from bioetl.domain.types import BronzeRecord


class DocumentTermTransformer(BaseChemblTransformer):
    """Transforms ChEMBL document records to extract flattened term records.

    This transformer extracts nested term data from Document API responses
    and flattens the 1:M relationship (one Document → multiple Terms).

    Term types extracted:
    - MESH_HEADING: MeSH descriptor terms from mesh_terms array
    - MESH_QUALIFIER: MeSH qualifiers/subheadings from mesh_terms
    - KEYWORD: Author-provided keywords from keywords array

    Entity ID is computed as SHA256 hash of composite key:
    (document_chembl_id, term_type, normalized_term)

    Note: This transformer returns multiple records from a single Document,
    unlike standard transformers that have 1:1 input/output mapping.
    """

    entity_class = DocumentTerm
    primary_id_field = "document_chembl_id"

    # Fields to exclude from content hash
    HASH_EXCLUDE_FIELDS: ClassVar[frozenset[str]] = frozenset(
        {
            "_run_id",
            "_run_type",
            "_source_batch_id",
            "_ingestion_ts",
            "_index",
        }
    )

    def _extract_business_data(
        self,
        record: BronzeRecord,
        primary_id: Any,
    ) -> dict[str, Any]:
        """Extract term data from the record.

        Handles two cases:
        1. Pre-extracted term records (from DocumentTermDataSource) - pass through
        2. Raw document records - extract terms from mesh_terms/keywords arrays

        Args:
            record: Bronze record (either term record or document record).
            primary_id: Validated document_chembl_id value.

        Returns:
            Dictionary of term business fields.

        """
        # Case 1: Record is already a term record (from DocumentTermDataSource)
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
        """Extract and flatten all terms from a Document record.

        Yields multiple term records from one document.
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
