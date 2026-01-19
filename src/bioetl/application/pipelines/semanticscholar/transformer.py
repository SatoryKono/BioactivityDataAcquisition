# src/bioetl/application/pipelines/semanticscholar/transformer.py
"""Semantic Scholar Publication Transformer.

Transforms Bronze records to Silver format (Publication entity).
Handles both DOI-resolved and title-fallback records.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from bioetl.application.pipelines.common import BasePublicationTransformer
from bioetl.application.pipelines.semanticscholar.extractors import (
    extract_authors,
    extract_external_ids,
    extract_fields_of_study,
    extract_journal_info,
    extract_open_access_info,
    extract_tldr,
    validate_year,
)
from bioetl.domain.entities.semanticscholar import SemanticScholarPublicationEntity
from bioetl.domain.value_objects import DOI, PubMedId

if TYPE_CHECKING:
    from bioetl.domain.filtering import GoldFilterConfig
    from bioetl.domain.ports import (
        DataNormalizationPort,
        MetricsPort,
        PiiHasherPort,
        TracingPort,
    )
    from bioetl.domain.services import IdentityService
    from bioetl.domain.types import BronzeRecord


class SemanticScholarPublicationTransformer(BasePublicationTransformer):
    """Transforms Semantic Scholar papers to Publication entity.

    Mapping:
    - paper_id: paperId (40-char hex S2 ID)
    - doi: externalIds.DOI
    - pmid: externalIds.PubMed
    - arxiv_id: externalIds.ArXiv
    - title: title
    - abstract: abstract
    - tldr: tldr.text (AI-generated summary)
    - authors: authors (extraction + optional PII hashing)
    - journal: journal.name / venue
    - year: year
    - publication_date: publicationDate
    - citation_count: citationCount
    - reference_count: referenceCount
    - is_oa: isOpenAccess (normalized)
    - oa_status: openAccessPdf.status (normalized to lowercase)
    - open_access_url: openAccessPdf.url
    - fields_of_study: fieldsOfStudy
    - publication_types: publicationTypes

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
        provider: str = "semanticscholar",
        entity_type: str = "publication",
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
        gold_filters: GoldFilterConfig | None = None,
        identity_service: IdentityService | None = None,
        pii_hasher: PiiHasherPort | None = None,
        data_normalizer: DataNormalizationPort | None = None,
    ) -> None:
        """Initialize transformer.

        Args:
            provider: Data provider identifier.
            entity_type: Entity type for metrics.
            tracer: Optional tracing port for distributed tracing.
            metrics: Optional metrics port for duration/error tracking.
            gold_filters: Optional filter configuration for Gold layer.
            identity_service: Service for computing entity IDs and content hashes.
            pii_hasher: Optional PII hasher for hashing author names.
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

    def _parse_pages(self, pages: str | None) -> tuple[str | None, str | None]:
        """Parse pages string into first_page and last_page.

        Handles formats like:
        - "123-456" -> ("123", "456")
        - "123" -> ("123", None)
        - "e123-e456" -> ("e123", "e456")
        - None or empty -> (None, None)

        Args:
            pages: Page string in "first-last" format.

        Returns:
            Tuple of (first_page, last_page).
        """
        if not pages or not pages.strip():
            return None, None

        pages = pages.strip()
        if "-" in pages:
            parts = pages.split("-", 1)
            first = parts[0].strip() or None
            last = parts[1].strip() if len(parts) > 1 and parts[1].strip() else None
            return first, last

        return pages, None

    def _normalize_pmc_id(self, pmc_id: str | None) -> str | None:
        """Ensure PMC ID has 'PMC' prefix.

        Normalizes PMC IDs to uppercase with 'PMC' prefix for consistency
        across providers.

        Args:
            pmc_id: Raw PMC ID (may or may not have prefix).

        Returns:
            Normalized PMC ID with 'PMC' prefix, or None if input is empty.
        """
        if not pmc_id:
            return None
        pmc_id = pmc_id.strip()
        if not pmc_id.upper().startswith("PMC"):
            return f"PMC{pmc_id}"
        return pmc_id.upper()

    def _extract_business_data(self, record: BronzeRecord) -> dict[str, Any]:
        """Extract and normalize fields from Semantic Scholar record.

        Args:
            record: Raw Bronze record from Semantic Scholar API.

        Returns:
            Dictionary of extracted and normalized fields.

        """
        rec = cast("dict[str, Any]", record)

        # Primary key - S2 Paper ID
        paper_id = rec.get("paperId")

        # External identifiers
        external_ids = extract_external_ids(rec.get("externalIds"))

        # Validate DOI using Value Object (returns None for invalid/empty)
        raw_doi = external_ids.get("doi")
        doi_vo = DOI.from_raw(raw_doi)
        doi = str(doi_vo) if doi_vo else None

        # Validate PMID using Value Object (returns None for invalid/empty)
        raw_pmid = external_ids.get("pmid")
        pmid_vo = PubMedId.from_raw(raw_pmid)
        pmid = str(pmid_vo) if pmid_vo else None

        # Authors with optional PII hashing
        raw_authors = extract_authors(rec.get("authors"))
        hashed_authors = self.hash_pii_list(raw_authors) or []

        # Journal/venue info
        journal_info = extract_journal_info(
            rec.get("journal"),
            rec.get("venue"),
        )

        # Parse pages into unified first_page/last_page
        pages = journal_info.get("pages")
        first_page, last_page = self._parse_pages(pages)

        # Open access info
        oa_info = extract_open_access_info(
            rec.get("isOpenAccess"),
            rec.get("openAccessPdf"),
        )

        # TLDR summary
        tldr = extract_tldr(rec.get("tldr"))

        # Fields of study
        fields_of_study = extract_fields_of_study(rec.get("fieldsOfStudy"))

        # Validate year
        year = validate_year(rec.get("year"))

        # Lookup metadata (from adapter)
        lookup_method = rec.get("_lookup_method", "unknown")
        original_id = rec.get("_original_id")

        return {
            "paper_id": paper_id,
            "doi": doi,
            "pmid": pmid,  # Use validated PMID from PubMedId Value Object
            "pmc_id": self._normalize_pmc_id(
                external_ids.get("pmcid")
            ),  # API uses "pmcid", we use "pmc_id"
            "arxiv_id": external_ids.get("arxiv"),
            "corpus_id": external_ids.get("corpus_id"),
            "title": rec.get("title"),
            "abstract": self._data_normalizer.strip_html_tags(rec.get("abstract")),
            "tldr": tldr,
            "authors": self.serialize_json_list(hashed_authors),
            "journal": journal_info.get("journal_name"),
            "volume": journal_info.get("volume"),
            "pages": pages,  # Legacy field
            "first_page": first_page,  # Unified field
            "last_page": last_page,  # Unified field
            "venue": rec.get("venue"),
            "year": year,
            "publication_date": rec.get("publicationDate"),
            "citation_count": rec.get("citationCount"),
            "reference_count": rec.get("referenceCount"),
            "is_oa": oa_info.get("is_oa"),
            "open_access_url": oa_info.get("url"),
            "oa_status": oa_info.get("oa_status"),
            "fields_of_study": self.serialize_json(fields_of_study),
            "publication_types": self.serialize_json(rec.get("publicationTypes")),
            "source": "semanticscholar",
            # Lookup metadata
            "_lookup_method": lookup_method,
            "_original_id": original_id,
            # DQ flags (default: no warnings or errors)
            "_dq_warn": False,
            "_dq_error": False,
        }

    def _get_primary_id_field(self) -> str:
        """Return the primary ID field name for Semantic Scholar publications.

        Returns:
            'paper_id' - the Semantic Scholar-specific identifier field.

        """
        return "paper_id"

    def _get_entity_class(self) -> type[SemanticScholarPublicationEntity]:
        """Return the domain entity class for Semantic Scholar publications.

        Returns:
            SemanticScholarPublicationEntity class.

        """
        return SemanticScholarPublicationEntity
