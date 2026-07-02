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


from collections.abc import Sequence
from typing import TYPE_CHECKING

from bioetl.application.pipelines.common import BasePublicationTransformer
from bioetl.application.pipelines.common.publication_issn import build_issn_fields
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
from bioetl.domain.types import GoldRecord
from bioetl.domain.value_objects import PublicationYear
from bioetl.domain.value_objects.publications import DOI

if TYPE_CHECKING:
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

    DEFAULT_PROVIDER = "openalex"
    DEFAULT_ENTITY_TYPE = "publication"

    # ========================================================================
    # Field Extraction Methods (Orchestration - delegates to extractors)
    # ========================================================================

    @staticmethod
    def _ensure_dict_list(value: object) -> list[dict[str, object]]:
        """Normalize untrusted JSON value to list[dict] for extractor contracts."""
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, dict)]

    def _serialize_json_list_or_none(
        self,
        values: Sequence[object],
        *,
        require_non_empty: bool = False,
        require_truthy_item: bool = False,
    ) -> str | None:
        """Serialize list to JSON string with configurable guard conditions."""
        if require_non_empty and not values:
            return None
        if require_truthy_item and not any(values):
            return None
        return self.serialize_json_list(values)

    def _extract_record_identity_bundle(self, rec: BronzeRecord) -> GoldRecord:
        """Extract identity/core text fields shared by all OpenAlex records."""
        abstract = self._data_normalizer.strip_html_tags(
            reconstruct_abstract(rec.get("abstract_inverted_index"))
        )
        return {
            "openalex_id": extract_openalex_id(rec.get("id")),
            "doi": self.validate_value_object(DOI, rec.get("doi")),
            "title": rec.get("title"),
            "abstract": abstract,
        }

    @staticmethod
    def _extract_lookup_metadata_bundle(rec: BronzeRecord) -> GoldRecord:
        """Extract lookup metadata fields used by quality/debug workflows."""
        return {
            "_lookup_method": rec.get("_lookup_method", "unknown"),
            "_original_id": rec.get("_original_id"),
            "_source": "openalex",
            "_dq_warn": False,
            "_dq_error": False,
        }
    def _extract_author_bundle(self, rec: BronzeRecord) -> GoldRecord:
        """Extract and normalize author/affiliation related fields."""
        normalizer = self._data_normalizer
        authorships = self._ensure_dict_list(rec.get("authorships", []))

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
            "institution_ids": self._serialize_json_list_or_none(
                extract_institution_ids(authorships)
            ),
            "institution_country_codes": self._serialize_json_list_or_none(
                extract_institution_country_codes(authorships)
            ),
            "ror_ids": self._serialize_json_list_or_none(
                ror_ids,
                require_non_empty=True,
            ),
            "author_orcids": self._serialize_json_list_or_none(
                author_orcids,
                require_truthy_item=True,
            ),
            "author_openalex_ids": self._serialize_json_list_or_none(
                author_openalex_ids,
                require_truthy_item=True,
            ),
        }

    def _extract_subject_bundle(self, rec: BronzeRecord) -> GoldRecord:
        """Extract topic, keyword, and grant classification fields."""
        subject_topics = extract_topics(self._ensure_dict_list(rec.get("topics", [])))
        primary_topic = extract_primary_topic(rec.get("primary_topic"))
        grant_records = (
            self._ensure_dict_list(rec.get("awards", []))
            or self._ensure_dict_list(rec.get("funders", []))
            or self._ensure_dict_list(rec.get("grants", []))
        )
        grants = extract_grants(grant_records)
        subject_mesh = extract_mesh_terms(self._ensure_dict_list(rec.get("mesh", [])))
        subject_keywords = extract_keywords(
            self._ensure_dict_list(rec.get("keywords", []))
        )

        return {
            "subject_topics": self._serialize_json_list_or_none(
                subject_topics,
                require_non_empty=True,
            ),
            "primary_topic": self.serialize_json(primary_topic)
            if primary_topic
            else None,
            "grants": self._serialize_json_list_or_none(
                grants,
                require_non_empty=True,
            ),
            "subject_mesh": self._serialize_json_list_or_none(subject_mesh),
            "subject_keywords": self._serialize_json_list_or_none(subject_keywords),
        }

    def _extract_publication_bundle(self, rec: BronzeRecord) -> GoldRecord:
        """Extract publication metadata and quality indicator fields."""
        external_ids = extract_external_ids(rec.get("ids", {}))
        journal_info = extract_journal_info(rec.get("primary_location", {}))
        issn_fields = build_issn_fields(
            journal_info.get("issn"),
            serialize_json_list=self.serialize_json_list,
        )
        biblio_info = extract_biblio_info(rec.get("biblio", {}))
        oa_info = extract_open_access_info(rec.get("open_access", {}))
        raw_publication_type = rec.get("type")
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
            **issn_fields,
            "publisher": journal_info.get("publisher"),
            "publication_year": year,
            "publication_date": self._data_normalizer.normalize_partial_date(
                rec.get("publication_date")
            ),
            **self._classify_publication_type(
                "openalex",
                raw_type=raw_publication_type,
            ),
            "type_crossref": rec.get("type_crossref"),
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
        identity_bundle = self._extract_record_identity_bundle(rec)
        author_bundle = self._extract_author_bundle(rec)
        subject_bundle = self._extract_subject_bundle(rec)
        publication_bundle = self._extract_publication_bundle(rec)

        return {
            **identity_bundle,
            **author_bundle,
            **publication_bundle,
            **subject_bundle,
            **self._extract_lookup_metadata_bundle(rec),
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
