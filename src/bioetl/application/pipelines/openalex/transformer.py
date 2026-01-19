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
    extract_external_ids,
    extract_journal_info,
    extract_keywords,
    extract_mesh_terms,
    extract_open_access_info,
    extract_openalex_id,
    reconstruct_abstract,
)
from bioetl.domain.entities.openalex import OPENALEX_TYPE_MAP, OpenAlexPublicationEntity
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
    - concepts: concepts (top-level only)

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
        doi_vo = DOI.from_raw(rec.get("doi"))
        doi = str(doi_vo) if doi_vo else None

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

        # Extract external IDs (pmid, pmc_id, mag)
        external_ids = extract_external_ids(rec.get("ids", {}))

        # Extract MeSH terms
        mesh_terms = extract_mesh_terms(rec.get("mesh", []))

        # Extract keywords
        keywords = extract_keywords(rec.get("keywords", []))

        # Validate year using PublicationYear Value Object
        year_vo = PublicationYear.from_raw(rec.get("publication_year"))
        year = year_vo.value if year_vo else None

        # Map document type
        raw_type = rec.get("type", "")
        doc_type = OPENALEX_TYPE_MAP.get(raw_type, "PUBLICATION")

        # Lookup metadata (from adapter)
        lookup_method = rec.get("_lookup_method", "unknown")
        original_id = rec.get("_original_id")

        return {
            "openalex_id": openalex_id,
            "doi": doi,
            "pmid": external_ids.get("pmid"),
            "pmc_id": external_ids.get("pmcid"),  # API uses "pmcid", we use "pmc_id"
            "mag_id": external_ids.get("mag_id"),
            "title": rec.get("title"),
            "abstract": abstract,
            "authors": self.serialize_json_list(hashed_authors),
            "journal": journal_info.get("journal_name"),
            "issn": journal_info.get("issn"),
            "publisher": journal_info.get("publisher"),
            "year": year,
            "publication_date": self._normalize_partial_date(rec.get("publication_date")),
            "doc_type": doc_type,
            "is_oa": oa_info.get("is_oa"),
            "oa_status": oa_info.get("oa_status"),
            # OpenAlex source field: cited_by_count
            # Unified BioETL field: citation_count (standardized across all providers)
            "citation_count": rec.get("cited_by_count"),
            "concepts": concepts,
            "mesh": mesh_terms,
            "keywords": keywords,
            "language": rec.get("language"),
            # Pages (OpenAlex doesn't provide page info in standard fields)
            "first_page": None,
            "last_page": None,
            "_lookup_method": lookup_method,
            "_original_id": original_id,
            "source": "openalex",
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

    def _normalize_partial_date(self, date_str: str | None) -> str | None:
        """Normalize partial date to YYYY-MM-DD format (end of period).

        OpenAlex API may return partial dates in various formats:
        - Full date: "2024-05-15" (YYYY-MM-DD)
        - Month precision: "2024-05" (YYYY-MM)
        - Year precision: "2024" (YYYY)

        Partial dates are normalized to end of period for consistency:
        - YYYY-MM → YYYY-MM-30 (approximate month end)
        - YYYY → YYYY-12-31 (year end)

        Args:
            date_str: Raw date string from OpenAlex API.

        Returns:
            Normalized ISO date string (YYYY-MM-DD) or None.

        """
        if not date_str:
            return None

        date_str = str(date_str).strip()

        # Full ISO format (YYYY-MM-DD) - return as-is
        if len(date_str) == 10 and date_str[4] == "-" and date_str[7] == "-":
            return date_str

        # Partial date: YYYY-MM → YYYY-MM-30 (end of month approximation)
        if len(date_str) == 7 and date_str[4] == "-":
            return f"{date_str}-30"

        # Partial date: YYYY → YYYY-12-31 (end of year)
        if len(date_str) == 4 and date_str.isdigit():
            return f"{date_str}-12-31"

        # Unknown format - return None for invalid dates
        return None
