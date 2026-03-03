"""ChEMBL Publication Term Transformer.

Transforms Publication records to extract and flatten associated terms.
This is a derived entity transformer - it extracts nested term data
from Publication (ChEMBL Document) API responses and flattens the 1:M relationship.

Uses declarative field_specs DSL for mapping.

.. versionchanged:: 2.0.0
    Renamed from document_term_transformer to publication_term_transformer (ADR-024).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from bioetl.domain.types import GoldRecord

from bioetl.application.core.entity_id import compute_publication_term_entity_id
from bioetl.application.pipelines.chembl.base_chembl_transformer import (
    BaseChemblTransformer,
)
from bioetl.domain.entities import DocumentTerm

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.types import BronzeRecord, PrimaryId, SilverRecord


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
    primary_id_field = "publication_id"

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
        # Support raw ChEMBL API field name for derived publication_term pipeline.
        # ChEMBL /document endpoint emits document_chembl_id, while pipeline contracts
        # use canonical publication_id.
        if (
            "publication_id" not in record
            and record.get("document_chembl_id") is not None
        ):
            record = dict(record)
            record["publication_id"] = record.get("document_chembl_id")

        # 1. Validate primary ID (publication_id)
        primary_id = self._get_required_field(record, self.primary_id_field)

        # 2. Extract business data (term details)
        business_data = self._extract_business_data(record, primary_id)

        # 3. Compute entity_id using composite key
        # Priority: pre-computed entity_id from record > computed from composite key
        pre_computed_id = record.get("entity_id")
        if pre_computed_id:
            entity_id = str(pre_computed_id)
        else:
            # Compute from composite key (publication_id, term_type, term)
            entity_id = self.compute_term_entity_id(
                publication_id=str(business_data.get("publication_id", primary_id)),
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
        primary_id: PrimaryId,
    ) -> GoldRecord:
        """Extract term data from the record.

        Handles two cases:
        1. Pre-extracted term records (from PublicationTermDataSource) - pass through
           with normalization (strip whitespace from term/term_type).
        2. Raw publication records - extract terms from mesh_terms/keywords arrays.

        Both paths apply consistent normalization via strip() on term and term_type
        to ensure storage consistency regardless of input source.

        Args:
            record: Bronze record (either term record or document record).
            primary_id: Validated publication_id value.

        Returns:
            Dictionary of term business fields with normalized values.

        """
        # Case 1: Record is already a term record (from PublicationTermDataSource)
        # These records have 'term' and 'term_type' fields directly.
        # Apply same normalization as _create_term_data for consistency.
        if "term" in record and "term_type" in record:
            raw_term = record.get("term")
            raw_term_type = record.get("term_type")
            raw_mesh_id = record.get("mesh_id")
            raw_qualifier = record.get("qualifier")

            # Normalize term and term_type (strip whitespace, convert to string)
            term = str(raw_term).strip() if raw_term else ""
            term_type = str(raw_term_type).strip() if raw_term_type else ""
            mesh_id = str(raw_mesh_id).strip() if raw_mesh_id else None
            qualifier = str(raw_qualifier).strip() if raw_qualifier else None

            return {
                "publication_id": str(record.get("publication_id", primary_id)),
                "term": term,
                "term_type": term_type,
                "mesh_id": mesh_id,
                "qualifier": qualifier,
            }

        # Case 2: Raw document record - extract terms from nested arrays
        terms = list(self.extract_terms_from_document(record, str(primary_id)))
        if not terms:
            # Return empty data that will fail validation
            return {
                "publication_id": str(primary_id),
                "term": "",
                "term_type": "",
                "mesh_id": None,
                "qualifier": None,
            }
        return terms[0]

    def extract_terms_from_document(
        self, record: BronzeRecord, publication_id: str
    ) -> list[GoldRecord]:
        """Extract and flatten all terms from a Publication record.

        Yields multiple term records from one publication.
        This is the primary method for derived entity extraction.

        Args:
            record: Raw Bronze record from ChEMBL API.
            publication_id: Document ChEMBL ID.

        Yields:
            Dictionary of term business fields for each term.

        Returns:
            Extracted value.
        """
        terms: list[GoldRecord] = []

        # Extract MeSH terms
        raw_mesh_terms = record.get("mesh_terms")
        mesh_terms: list[Any] = (  # Any: untyped ChEMBL API JSON list elements
            raw_mesh_terms if isinstance(raw_mesh_terms, list) else []
        )
        for mesh in mesh_terms:
            if not isinstance(mesh, dict):
                continue

            mesh_heading = mesh.get("mesh_heading")
            if mesh_heading:
                terms.append(
                    self._create_term_data(
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
                    self._create_term_data(
                        publication_id=publication_id,
                        term=mesh_qualifier,
                        term_type="MESH_QUALIFIER",
                        mesh_id=mesh.get("mesh_id"),
                        qualifier=None,
                    )
                )

        # Extract keywords
        raw_keywords = record.get("keywords")
        keywords: list[Any] = raw_keywords if isinstance(raw_keywords, list) else []  # Any: untyped ChEMBL API JSON list elements
        for keyword in keywords:
            if isinstance(keyword, str):
                stripped = keyword.strip()
                if stripped:  # Skip empty strings after stripping
                    terms.append(
                        self._create_term_data(
                            publication_id=publication_id,
                            term=stripped,
                            term_type="KEYWORD",
                            mesh_id=None,
                            qualifier=None,
                        )
                    )

        return terms

    def _create_term_data(
        self,
        publication_id: str,
        term: str,
        term_type: str,
        mesh_id: str | None,
        qualifier: str | None,
    ) -> GoldRecord:
        """Create a single term data dictionary.

        Args:
            publication_id: Parent document ChEMBL ID.
            term: Term text.
            term_type: Term type (MESH_HEADING, MESH_QUALIFIER, KEYWORD, CONCEPT).
            mesh_id: MeSH identifier if applicable.
            qualifier: MeSH qualifier if applicable.

        Returns:
            Dictionary of term business fields.

        """
        return {
            "publication_id": publication_id,
            "term": term.strip() if term else term,
            "term_type": term_type,
            "mesh_id": mesh_id,
            "qualifier": qualifier,
        }

    def compute_term_entity_id(
        self, publication_id: str, term_type: str, term: str
    ) -> str:
        """Compute entity ID for a term based on composite key.

        Delegates to shared ``compute_publication_term_entity_id``.

        Args:
            document_chembl_id: Document ChEMBL ID.
            term_type: Term type classification.
            term: Term text (will be normalized).

        Returns:
            Entity ID string (first 16 chars of SHA256 hex digest).

        """
        return compute_publication_term_entity_id(publication_id, term_type, term)
