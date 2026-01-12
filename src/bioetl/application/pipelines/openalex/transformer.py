"""OpenAlex Publication Transformer.

Transforms Bronze records to Silver format (OpenAlexPublicationEntity).
Handles both DOI-resolved and title-fallback records.

This module contains orchestration logic for OpenAlex data transformation
per Hexagonal Architecture.

Terminology:
- Uses "Publication" instead of OpenAlex API term "Work" for Ubiquitous Language
- All layers use "publication" to refer to scholarly works

Note: Business logic functions are delegated to extractors module.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from bioetl.application.pipelines.common import BasePublicationTransformer
from bioetl.application.pipelines.openalex.extractors import (
    extract_authors,
    extract_concepts,
    extract_doi,
    extract_journal_info,
    extract_open_access_info,
    extract_openalex_id,
    reconstruct_abstract,
)
from bioetl.domain.entities.openalex import OPENALEX_TYPE_MAP, OpenAlexPublicationEntity
from bioetl.domain.services import DataNormalizationService, IdentityService
from bioetl.domain.validation import validate_year_range

if TYPE_CHECKING:
    from bioetl.domain.filtering import GoldFilterConfig
    from bioetl.domain.ports import (
        DataNormalizationPort,
        MetricsPort,
        PiiHasherPort,
        TracingPort,
    )
    from bioetl.domain.types import BronzeRecord


class OpenAlexPublicationTransformer(BasePublicationTransformer):
    """Transforms OpenAlex Works to Publication entity.

    Mapping:
    - openalex_id: id (URL -> ID extraction)
    - doi: doi (URL -> bare DOI)
    - title: title
    - abstract: abstract_inverted_index (reconstruction)
    - authors: authorships (extraction + PII hashing)
    - journal: primary_location.source.display_name
    - year: publication_year
    - concepts: concepts (top-level only)

    Handles lookup metadata:
    - _lookup_method: "doi" | "title_fallback" | "title_only"
    - _original_doi: Original DOI for fallback records

    Subclasses BasePublicationTransformer to provide:
    - Unified transformation flow via Template Method
    - Automatic primary ID validation and fallback logging
    - Content hash computation (excluding metadata)
    - Tracing and metrics observability (O1)
    """

    def __init__(
        self,
        provider: str = "openalex",
        entity_type: str = "publication",
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
        gold_filters: GoldFilterConfig | None = None,
        identity_service: IdentityService | None = None,
        pii_hasher: PiiHasherPort | None = None,
        data_normalizer: DataNormalizationPort | None = None,
    ) -> None:
        """Initialize OpenAlex transformer.

        Args:
            provider: Data provider identifier. Defaults to 'openalex'.
            entity_type: Entity type for metrics labels. Defaults to 'publication'.
            tracer: Optional tracing port for distributed tracing.
            metrics: Optional metrics port for duration/error tracking.
            gold_filters: Optional filter configuration for Gold layer.
            identity_service: Service for computing entity IDs and content hashes.
            pii_hasher: Optional PII hasher for hashing author names (RULES.md S5.4).
            data_normalizer: Optional data normalization service for DOI normalization.

        """
        super().__init__(
            provider,
            entity_type=entity_type,
            tracer=tracer,
            metrics=metrics,
            gold_filters=gold_filters,
            identity_service=identity_service,
            pii_hasher=pii_hasher,
        )
        self._data_normalizer = data_normalizer or DataNormalizationService()

    # ========================================================================
    # Field Extraction Methods (Orchestration - delegates to extractors)
    # ========================================================================

    def _extract_business_data(self, record: BronzeRecord) -> dict[str, Any]:
        """Extract Publication business data from bronze record.

        Delegates field extraction to extractors module per REFACTOR-004.

        Args:
            record: Raw Bronze record from OpenAlex API.

        Returns:
            Dictionary of Publication business fields.

        """
        # Cast to dict for type-safe access (BronzeRecord is a TypedDict marker)
        rec = cast("dict[str, Any]", record)

        # Extract OpenAlex ID from URL
        openalex_id = extract_openalex_id(rec.get("id"))

        # Extract bare DOI from URL, then normalize (lowercase, stripped)
        # for cross-provider consistency
        raw_doi = extract_doi(rec.get("doi"))
        doi = self._data_normalizer.normalize_doi(raw_doi)

        # Reconstruct abstract from inverted index (then strip HTML for cleaning)
        abstract_index = rec.get("abstract_inverted_index")
        abstract = self._data_normalizer.strip_html_tags(
            reconstruct_abstract(abstract_index)
        )

        # Extract and hash authors (PII)
        # Authors stored as JSON-serialized list for unified format across providers
        raw_authors = extract_authors(rec.get("authorships", []))
        hashed_authors = self.hash_pii_list(raw_authors) or []

        # Extract journal info
        journal_info = extract_journal_info(rec.get("primary_location", {}))

        # Extract concepts
        concepts = extract_concepts(rec.get("concepts", []))

        # Extract Open Access info
        oa_info = extract_open_access_info(rec.get("open_access", {}))

        # Validate year
        year = rec.get("publication_year")
        if year is not None and not validate_year_range(year):
            year = None

        # Map document type
        raw_type = rec.get("type", "")
        doc_type = OPENALEX_TYPE_MAP.get(raw_type, "PUBLICATION")

        # Lookup metadata (from adapter)
        lookup_method = rec.get("_lookup_method", "unknown")
        original_doi = rec.get("_original_doi")

        return {
            "openalex_id": openalex_id,
            "doi": doi,
            "title": rec.get("title"),
            "abstract": abstract,
            "authors": self.serialize_json_list(hashed_authors),
            "journal": journal_info.get("journal_name"),
            "issn": journal_info.get("issn"),
            "publisher": journal_info.get("publisher"),
            "year": year,
            "publication_date": rec.get("publication_date"),
            "doc_type": doc_type,
            "is_oa": oa_info.get("is_oa"),
            "oa_status": oa_info.get("oa_status"),
            # OpenAlex source field: cited_by_count
            # Unified BioETL field: citation_count (standardized across all providers)
            "citation_count": rec.get("cited_by_count"),
            "concepts": concepts,
            "language": rec.get("language"),
            "_lookup_method": lookup_method,
            "_original_doi": original_doi,
            "source": "openalex",
        }

    def _get_primary_id_field(self) -> str:
        """Return the primary ID field name for OpenAlex publications.

        Returns:
            'openalex_id' - the OpenAlex-specific identifier field.

        """
        return "openalex_id"

    def _get_entity_class(self) -> type[OpenAlexPublicationEntity]:
        """Return the domain entity class for OpenAlex publications.

        Returns:
            OpenAlexPublicationEntity class.

        """
        return OpenAlexPublicationEntity
