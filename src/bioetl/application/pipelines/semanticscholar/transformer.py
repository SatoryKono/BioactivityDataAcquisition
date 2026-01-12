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
from bioetl.domain.normalization import strip_html_tags

if TYPE_CHECKING:
    from bioetl.domain.filtering import GoldFilterConfig
    from bioetl.domain.ports import MetricsPort, PiiHasherPort, TracingPort
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
        provider: str = "semanticscholar",
        entity_type: str = "publication",
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
        gold_filters: GoldFilterConfig | None = None,
        identity_service: IdentityService | None = None,
        pii_hasher: PiiHasherPort | None = None,
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
        doi = external_ids.get("doi")

        # Authors with optional PII hashing
        raw_authors = extract_authors(rec.get("authors"))
        hashed_authors = self.hash_pii_list(raw_authors) or []

        # Journal/venue info
        journal_info = extract_journal_info(
            rec.get("journal"),
            rec.get("venue"),
        )

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
        original_doi = rec.get("_original_doi")

        return {
            "paper_id": paper_id,
            "doi": doi,
            "pmid": external_ids.get("pmid"),
            "pmcid": external_ids.get("pmcid"),
            "arxiv_id": external_ids.get("arxiv"),
            "corpus_id": external_ids.get("corpus_id"),
            "title": rec.get("title"),
            "abstract": strip_html_tags(rec.get("abstract")),
            "tldr": tldr,
            "authors": self.serialize_json_list(hashed_authors),
            "journal": journal_info.get("journal_name"),
            "volume": journal_info.get("volume"),
            "pages": journal_info.get("pages"),
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
            "_original_doi": original_doi,
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
