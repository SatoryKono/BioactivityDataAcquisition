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
    extract_affiliations,
    extract_authors,
    extract_biblio_info,
    extract_concepts,
    extract_external_ids,
    extract_grants,
    extract_institution_country_codes,
    extract_institution_ids,
    extract_journal_info,
    extract_keywords,
    extract_mesh_terms,
    extract_open_access_info,
    extract_openalex_id,
    extract_primary_topic,
    extract_topics,
    reconstruct_abstract,
)
from bioetl.domain.entities.openalex import OpenAlexPublicationEntity
from bioetl.domain.services import IdentityService
from bioetl.domain.value_objects import DOI, PublicationYear

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
    - topics: topics (hierarchical 4-level classification)
    - primary_topic: primary_topic (single most relevant topic)
    - grants: grants (funding information)
    - concepts: concepts (DEPRECATED - kept for backward compatibility)

    Handles lookup metadata:
    - _lookup_method: "direct" | "doi" | "pmid" | "title_fallback" | "unknown"
    - _original_id: Original identifier used for lookup

    Subclasses BasePublicationTransformer to provide:
    - Unified transformation flow via Template Method
    - Automatic primary ID validation and fallback logging
    - Content hash computation (excluding metadata)
    - Tracing and metrics observability (O1)

    Note on Topics vs Concepts:
    - OpenAlex deprecated the `concepts` field in 2024 in favor of `topics`
    - Both fields are extracted during the transition period
    - New downstream code should use `topics` and `primary_topic`
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
            data_normalizer=data_normalizer,
        )

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

        # Validate DOI using Value Object (returns None for invalid/empty)
        # OpenAlex stores DOIs as full URLs (e.g., "https://doi.org/10.1038/...")
        doi = self.validate_value_object(DOI, rec.get("doi"))

        # Reconstruct abstract from inverted index (then strip HTML for cleaning)
        abstract_index = rec.get("abstract_inverted_index")
        abstract = self._data_normalizer.strip_html_tags(
            reconstruct_abstract(abstract_index)
        )

        # Extract and hash authors (PII)
        # Authors stored as JSON-serialized list for unified format across providers
        raw_authors = extract_authors(rec.get("authorships", []))
        hashed_authors = self.hash_pii_list(raw_authors) or []

        # Extract affiliations
        raw_affiliations = extract_affiliations(rec.get("authorships", []))
        serialized_affiliations = self.serialize_json_list(raw_affiliations)

        # Extract institution IDs and country codes (for cross-referencing and geographic analysis)
        institution_ids = extract_institution_ids(rec.get("authorships", []))
        institution_country_codes = extract_institution_country_codes(
            rec.get("authorships", [])
        )

        # Extract journal info
        journal_info = extract_journal_info(rec.get("primary_location", {}))

        # Extract topics (hierarchical classification - replaces deprecated concepts)
        topics = extract_topics(rec.get("topics", []))

        # Extract primary topic (single most relevant topic)
        primary_topic = extract_primary_topic(rec.get("primary_topic"))

        # Extract grants/funding information
        grants = extract_grants(rec.get("grants", []))

        # Extract concepts (DEPRECATED - kept for backward compatibility)
        concepts = extract_concepts(rec.get("concepts", []))

        # Extract Open Access info
        oa_info = extract_open_access_info(rec.get("open_access", {}))

        # Extract external IDs (pmid, pmc_id, mag)
        external_ids = extract_external_ids(rec.get("ids", {}))

        # Extract MeSH terms
        mesh_terms = extract_mesh_terms(rec.get("mesh", []))

        # Extract keywords
        keywords = extract_keywords(rec.get("keywords", []))

        # Extract bibliographic info (volume, issue, pages)
        biblio_info = extract_biblio_info(rec.get("biblio", {}))

        # Validate year using PublicationYear Value Object
        year = self.validate_value_object(
            PublicationYear, rec.get("publication_year"), as_string=False
        )

        # Lookup metadata (from adapter)
        lookup_method = rec.get("_lookup_method", "unknown")
        original_id = rec.get("_original_id")

        return {
            "openalex_id": openalex_id,
            "doi": doi,
            "pmid": external_ids.get("pmid"),
            "mag_id": external_ids.get("mag_id"),
            "title": rec.get("title"),
            "abstract": abstract,
            "authors": self.serialize_json_list(hashed_authors),
            "affiliations": serialized_affiliations,
            "institution_ids": institution_ids,
            "institution_country_codes": institution_country_codes,
            "journal": journal_info.get("journal_name"),
            "issn": journal_info.get("issn"),
            "publisher": journal_info.get("publisher"),
            "year": year,
            "publication_date": self._normalize_partial_date(
                rec.get("publication_date")
            ),
            "type": rec.get("type"),
            "is_oa": oa_info.get("is_oa"),
            "oa_status": oa_info.get("oa_status"),
            # OpenAlex source field: cited_by_count
            # Unified BioETL field: citation_count (standardized across all providers)
            "citation_count": rec.get("cited_by_count"),
            # Topics (hierarchical classification - replaces deprecated concepts)
            "topics": topics,
            "primary_topic": primary_topic,
            # Grants/funding information
            "grants": grants,
            # Concepts (DEPRECATED - kept for backward compatibility)
            "concepts": concepts,
            "mesh": mesh_terms,
            "keywords": keywords,
            "language": rec.get("language"),
            # Bibliographic info (from biblio object)
            "volume": biblio_info.get("volume"),
            "issue": biblio_info.get("issue"),
            "first_page": biblio_info.get("first_page"),
            "last_page": biblio_info.get("last_page"),
            # Additional metrics
            "fwci": rec.get("fwci"),
            "referenced_works_count": rec.get("referenced_works_count"),
            # Quality indicators
            "is_retracted": rec.get("is_retracted", False),
            "_lookup_method": lookup_method,
            "_original_id": original_id,
            "_source": "openalex",
            # DQ flags (default: no warnings or errors)
            "_dq_warn": False,
            "_dq_error": False,
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

    @staticmethod
    def entity_to_silver_record(entity: Any) -> dict[str, Any]:
        """Convert Domain Entity to SilverRecord, excluding pmc_id and doc_type.

        Overrides base implementation to remove fields not collected for OpenAlex.
        OpenAlex uses raw 'type' field instead of mapped 'doc_type'.

        Args:
            entity: Domain entity (dataclass).

        Returns:
            SilverRecord dictionary without pmc_id and doc_type fields.

        """
        from bioetl.application.core.base_transformer import BaseTransformer

        # Get base silver record
        silver_record = BaseTransformer.entity_to_silver_record(entity)

        # Remove excluded fields
        silver_record.pop("pmc_id", None)
        silver_record.pop("doc_type", None)  # OpenAlex uses raw 'type' instead

        return silver_record
