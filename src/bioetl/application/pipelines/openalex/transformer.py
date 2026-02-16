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

from typing import TYPE_CHECKING, Any

from bioetl.application.pipelines.common import BasePublicationTransformer
from bioetl.application.pipelines.openalex.extractors import (
    extract_affiliations,
    extract_author_ids,
    extract_author_orcids,
    extract_authors,
    extract_biblio_info,
    extract_external_ids,
    extract_grants,
    extract_institution_country_codes,
    extract_institution_ids,
    extract_institution_ror_ids,
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
    from bioetl.domain.filtering import GoldFilterConfig, SilverFilterConfig
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
    - subject_topics: topics (hierarchical 4-level classification)
    - primary_topic: primary_topic (single most relevant topic)
    - grants: grants (funding information)

    Handles lookup metadata:
    - _lookup_method: "direct" | "doi" | "pmid" | "title_fallback" | "unknown"
    - _original_id: Original identifier used for lookup

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
        silver_filters: SilverFilterConfig | None = None,
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
            silver_filters: Optional filter configuration for Silver layer.
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
            silver_filters=silver_filters,
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
        # BronzeRecord is already a dict[str, Any]
        rec = record

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

        # Extract and normalize authors using unified service (PII)
        normalizer = self._data_normalizer
        salt = (
            self._pii_hasher.get_salt() if hasattr(self._pii_hasher, "get_salt") else ""
        )

        raw_authors = extract_authors(rec.get("authorships", []))
        authors_json = normalizer.normalize_author_list(raw_authors)

        # Extract and normalize affiliations using unified service
        authorships = rec.get("authorships")
        raw_affiliations = (
            extract_affiliations(authorships) if isinstance(authorships, list) else None
        )
        affiliations_json = (
            normalizer.normalize_affiliations(raw_affiliations)
            if raw_affiliations
            else None
        )

        # Extract institution IDs and country codes (for cross-referencing and geographic analysis)
        institution_ids = extract_institution_ids(rec.get("authorships", []))
        institution_country_codes = extract_institution_country_codes(
            rec.get("authorships", [])
        )

        # Extract ROR IDs (may be empty if not returned by Works API)
        ror_ids = extract_institution_ror_ids(rec.get("authorships", []))

        # Extract author identifiers (ORCID and OpenAlex IDs)
        author_orcids = extract_author_orcids(rec.get("authorships", []))
        author_openalex_ids = extract_author_ids(rec.get("authorships", []))

        # Extract journal info
        journal_info = extract_journal_info(rec.get("primary_location", {}))

        # Extract topics (hierarchical classification - replaces deprecated concepts)
        subject_topics = extract_topics(rec.get("topics", []))

        # Extract primary topic (single most relevant topic)
        primary_topic = extract_primary_topic(rec.get("primary_topic"))

        # Extract grants/funding information
        grants = extract_grants(rec.get("grants", []))

        # Extract Open Access info
        oa_info = extract_open_access_info(rec.get("open_access", {}))

        # Extract external IDs (pmid, pmc_id, mag)
        external_ids = extract_external_ids(rec.get("ids", {}))

        # Extract MeSH terms
        subject_mesh = extract_mesh_terms(rec.get("mesh", []))

        # Extract keywords
        subject_keywords = extract_keywords(rec.get("keywords", []))

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
            "pmc_id": None,  # Not available from OpenAlex API
            "mag_id": external_ids.get("mag_id"),
            "title": rec.get("title"),
            "abstract": abstract,
            "authors": authors_json,
            "affiliation_list": affiliations_json,
            "institution_ids": institution_ids,
            "institution_country_codes": institution_country_codes,
            # ROR IDs (may be empty if not returned by Works API)
            "ror_ids": self.serialize_json_list(ror_ids) if ror_ids else None,
            "author_orcids": (
                self.serialize_json_list(author_orcids) if any(author_orcids) else None
            ),
            "author_openalex_ids": (
                self.serialize_json_list(author_openalex_ids)
                if any(author_openalex_ids)
                else None
            ),
            "journal": journal_info.get("journal"),
            "issn": journal_info.get("issn"),
            "publisher": journal_info.get("publisher"),
            "publication_year": year,
            "publication_date": self._data_normalizer.normalize_partial_date(
                rec.get("publication_date")
            ),
            "publication_type": rec.get("type"),  # Raw OpenAlex type
            **self._classify_publication_type("openalex", raw_type=rec.get("type")),
            "is_oa": oa_info.get("is_oa"),
            "oa_status": oa_info.get("oa_status"),
            # OpenAlex source field: cited_by_count
            # Unified BioETL field: citations_received (standardized across all providers)
            "citations_received": rec.get("cited_by_count"),
            # Topics (hierarchical classification - replaces deprecated concepts)
            # Serialized to JSON string for schema compliance
            "subject_topics": (
                self.serialize_json_list(subject_topics) if subject_topics else None
            ),
            "primary_topic": self.serialize_json(primary_topic)
            if primary_topic
            else None,
            # Grants/funding information (serialized to JSON string)
            "grants": self.serialize_json_list(grants) if grants else None,
            "subject_mesh": subject_mesh,
            "subject_keywords": subject_keywords,
            "language": rec.get("language"),
            # Bibliographic info (from biblio object)
            "volume": biblio_info.get("volume"),
            "issue": biblio_info.get("issue"),
            "page_first": biblio_info.get("page_first"),
            "page_last": biblio_info.get("page_last"),
            # Additional metrics
            "fwci": rec.get("fwci"),
            "citations_made": rec.get("referenced_works_count"),
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
        """Convert Domain Entity to SilverRecord.

        OpenAlex doesn't provide pmc_id, so it will be None in the entity.
        This None value satisfies the PublicationBaseSchema inheritance requirement.

        Args:
            entity: Domain entity (dataclass).

        Returns:
            SilverRecord dictionary with all PublicationBaseSchema fields.

        """
        from bioetl.application.core.base_transformer import BaseTransformer

        # Get base silver record (includes all fields with None values)
        silver_record = BaseTransformer.entity_to_silver_record(entity)

        # Note: pmc_id is kept (with None value) to satisfy PublicationBaseSchema

        return silver_record
