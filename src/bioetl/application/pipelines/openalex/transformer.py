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

__all__ = ["OpenAlexPublicationTransformer"]


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
from bioetl.domain.mapping.publication_type_mapping import normalize_publication_type
from bioetl.domain.services import IdentityService
from bioetl.domain.types import GoldRecord
from bioetl.domain.value_objects import DOI, PublicationYear

if TYPE_CHECKING:
    from bioetl.domain.filtering import GoldFilterConfig, SilverFilterConfig
    from bioetl.domain.ports import (
        ContractPolicyPort,
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
        contract_policy: ContractPolicyPort | None = None,
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
            contract_policy: Optional pipeline contract policy.

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
            contract_policy=contract_policy,
        )

    # ========================================================================
    # Field Extraction Methods (Orchestration - delegates to extractors)
    # ========================================================================

    def _extract_author_bundle(self, rec: BronzeRecord) -> GoldRecord:
        """Extract and normalize author/affiliation related fields."""
        normalizer = self._data_normalizer
        authorships_raw = rec.get("authorships", [])
        authorships = authorships_raw if isinstance(authorships_raw, list) else []

        raw_authors = extract_authors(authorships)
        raw_affiliations = extract_affiliations(authorships) if authorships else None
        author_orcids = extract_author_orcids(authorships)
        author_openalex_ids = extract_author_ids(authorships)
        ror_ids = extract_institution_ror_ids(authorships)

        return {
            "authors": normalizer.normalize_author_list(raw_authors),
            "author_keys": normalizer.normalize_author_keys(raw_authors),
            "affiliation_list": (
                normalizer.normalize_affiliations(raw_affiliations)
                if raw_affiliations
                else None
            ),
            "institution_ids": self.serialize_json_list(
                extract_institution_ids(authorships)
            ),
            "institution_country_codes": self.serialize_json_list(
                extract_institution_country_codes(authorships)
            ),
            "ror_ids": self.serialize_json_list(ror_ids) if ror_ids else None,
            "author_orcids": self.serialize_json_list(author_orcids)
            if any(author_orcids)
            else None,
            "author_openalex_ids": self.serialize_json_list(author_openalex_ids)
            if any(author_openalex_ids)
            else None,
        }

    def _extract_subject_bundle(self, rec: BronzeRecord) -> GoldRecord:
        """Extract topic, keyword, and grant classification fields."""
        subject_topics = extract_topics(rec.get("topics", []))
        primary_topic = extract_primary_topic(rec.get("primary_topic"))
        grants = extract_grants(rec.get("grants", []))
        subject_mesh = extract_mesh_terms(rec.get("mesh", []))
        subject_keywords = extract_keywords(rec.get("keywords", []))

        return {
            "subject_topics": (
                self.serialize_json_list(subject_topics) if subject_topics else None
            ),
            "primary_topic": self.serialize_json(primary_topic)
            if primary_topic
            else None,
            "grants": self.serialize_json_list(grants) if grants else None,
            "subject_mesh": self.serialize_json_list(subject_mesh),
            "subject_keywords": self.serialize_json_list(subject_keywords),
        }

    def _extract_publication_bundle(self, rec: BronzeRecord) -> GoldRecord:
        """Extract publication metadata and quality indicator fields."""
        external_ids = extract_external_ids(rec.get("ids", {}))
        journal_info = extract_journal_info(rec.get("primary_location", {}))
        biblio_info = extract_biblio_info(rec.get("biblio", {}))
        oa_info = extract_open_access_info(rec.get("open_access", {}))
        year = self.validate_value_object(
            PublicationYear,
            rec.get("publication_year"),
            as_string=False,
        )

        return {
            "pmid": external_ids.get("pmid"),
            "pmc_id": None,
            "mag_id": external_ids.get("mag_id"),
            "journal": journal_info.get("journal"),
            "issn": journal_info.get("issn"),
            "publisher": journal_info.get("publisher"),
            "publication_year": year,
            "publication_date": self._data_normalizer.normalize_partial_date(
                rec.get("publication_date")
            ),
            "publication_type": normalize_publication_type(rec.get("type")),
            **self._classify_publication_type("openalex", raw_type=rec.get("type")),
            "is_oa": oa_info.get("is_oa"),
            "oa_status": oa_info.get("oa_status"),
            "citations_received": rec.get("cited_by_count"),
            "language": rec.get("language"),
            "volume": biblio_info.get("volume"),
            "issue": biblio_info.get("issue"),
            "page_first": biblio_info.get("page_first"),
            "page_last": biblio_info.get("page_last"),
            "fwci": rec.get("fwci"),
            "citations_made": rec.get("referenced_works_count"),
            "is_retracted": rec.get("is_retracted", False),
        }

    def _extract_business_data(self, record: BronzeRecord) -> GoldRecord:
        """Extract Publication business data from bronze record.

        Delegates field extraction to extractors module per REFACTOR-004.

        Args:
            record: Raw Bronze record from OpenAlex API.

        Returns:
            Dictionary of Publication business fields.

        """
        rec = record
        abstract = self._data_normalizer.strip_html_tags(
            reconstruct_abstract(rec.get("abstract_inverted_index"))
        )
        author_bundle = self._extract_author_bundle(rec)
        subject_bundle = self._extract_subject_bundle(rec)
        publication_bundle = self._extract_publication_bundle(rec)

        return {
            "openalex_id": extract_openalex_id(rec.get("id")),
            "doi": self.validate_value_object(DOI, rec.get("doi")),
            "title": rec.get("title"),
            "abstract": abstract,
            **author_bundle,
            **publication_bundle,
            **subject_bundle,
            "_lookup_method": rec.get("_lookup_method", "unknown"),
            "_original_id": rec.get("_original_id"),
            "_source": "openalex",
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

        # Any: generic domain entity; type varies by pipeline

    def entity_to_silver_record(
        self,
        entity: Any,  # Any: generic domain entity; type varies by pipeline
    ) -> GoldRecord:  # Any: generic domain entity
        """Convert Domain Entity to SilverRecord.

        OpenAlex doesn't provide pmc_id, so it will be None in the entity.
        This None value satisfies the PublicationBaseSchema inheritance requirement.

        Args:
            entity: Domain entity (dataclass).

        Returns:
            SilverRecord dictionary with all PublicationBaseSchema fields.

        """
        # Get base silver record (includes all fields with None values)
        silver_record = super().entity_to_silver_record(entity)

        # Note: pmc_id is kept (with None value) to satisfy PublicationBaseSchema

        return silver_record
