# src/bioetl/application/pipelines/semanticscholar/transformer.py
"""Semantic Scholar Publication Transformer.

Transforms Bronze records to Silver format (Publication entity).
Handles both DOI-resolved and title-fallback records.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from bioetl.application.pipelines.common import BasePublicationTransformer
from bioetl.application.pipelines.semanticscholar.extractors import (
    extract_affiliations,
    extract_author_h_indices,
    extract_author_ids,
    extract_author_orcids,
    extract_author_s2_ids,
    extract_citation_contexts,
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
    - dblp_id: externalIds.DBLP
    - title: title
    - abstract: abstract
    - tldr: tldr.text (AI-generated summary)
    - authors: authors.name (extraction + optional PII hashing)
    - author_s2_ids: authors.authorId (S2 author IDs for disambiguation)
    - author_orcids: authors.externalIds.ORCID (persistent researcher IDs)
    - author_h_indices: authors.hIndex (research impact metric)
    - journal: journal.name / venue
    - year: year
    - publication_date: publicationDate
    - citation_count: citationCount
    - reference_count: referenceCount
    - influential_citation_count: influentialCitationCount
    - is_oa: isOpenAccess (normalized)
    - oa_status: openAccessPdf.status (normalized to lowercase)
    - open_access_url: openAccessPdf.url
    - fields_of_study: fieldsOfStudy
    - publication_types: publicationTypes
    - citation_contexts: citations.contexts (citing sentences, when available)

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

        # Get authors list for multiple extractions
        authors_list = rec.get("authors")

        # Extract author IDs
        author_ids = extract_author_ids(rec.get("authors"))

        # Extract author identifiers (for author-level analytics)
        author_s2_ids = extract_author_s2_ids(authors_list)
        author_orcids = extract_author_orcids(authors_list)
        author_h_indices = extract_author_h_indices(authors_list)

        # Extract affiliations from authors
        affiliations = extract_affiliations(authors_list)

        # Extract citation contexts (if available from citations/references endpoint)
        # Note: contexts are only available when requesting citation details
        citation_contexts = extract_citation_contexts(rec.get("citations"))

        # Journal/venue info with parsed volume/issue and pages
        # extract_journal_info now parses combined volume/issue (e.g., "32 4")
        # and expands abbreviated page ranges (e.g., "737-9" → 737-739)
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
        original_id = rec.get("_original_id")

        return {
            "paper_id": paper_id,
            "doi": doi,
            "pmid": pmid,  # Use validated PMID from PubMedId Value Object
            "dblp_id": external_ids.get("dblp"),
            "corpus_id": external_ids.get("corpus_id"),
            "title": rec.get("title"),
            # abstract, authors excluded per user request
            "tldr": tldr,
            "author_ids": self.serialize_json(author_ids),
            # Author identifiers (for author-level analytics and disambiguation)
            "author_s2_ids": self.serialize_json_list(author_s2_ids)
            if author_s2_ids
            else None,
            "author_orcids": self.serialize_json_list(author_orcids)
            if any(author_orcids)
            else None,
            "author_h_indices": self.serialize_json_list(author_h_indices)
            if any(h is not None for h in author_h_indices)
            else None,
            # Citation context (for citation sentiment analysis)
            "citation_contexts": self.serialize_json_list(citation_contexts)
            if citation_contexts
            else None,
            # Author affiliations (unique, sorted)
            "affiliations": self.serialize_json_list(affiliations)
            if affiliations
            else None,
            "journal": journal_info.get("journal_name"),
            "volume": journal_info.get("volume"),
            "issue": journal_info.get("issue"),  # Parsed from combined "32 4" format
            "pages": journal_info.get("pages"),  # Original pages string (cleaned)
            "first_page": journal_info.get(
                "first_page"
            ),  # Parsed with abbreviation expansion
            "last_page": journal_info.get("last_page"),  # Expanded (e.g., "9" → "739")
            "year": year,
            "publication_date": self._normalize_partial_date(
                rec.get("publicationDate")
            ),
            "citation_count": rec.get("citationCount"),
            "reference_count": rec.get("referenceCount"),
            "influential_citation_count": rec.get("influentialCitationCount"),
            "is_oa": oa_info.get("is_oa"),
            "open_access_url": oa_info.get("url"),
            "oa_status": oa_info.get("oa_status"),
            "fields_of_study": self.serialize_json(fields_of_study),
            "publication_types": self.serialize_json(rec.get("publicationTypes")),
            "_source": "semanticscholar",
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

    @staticmethod
    def entity_to_silver_record(entity: Any) -> dict[str, Any]:
        """Convert Domain Entity to SilverRecord, excluding unused fields.

        Overrides base implementation to remove fields not collected for S2.

        Args:
            entity: Domain entity (dataclass).

        Returns:
            SilverRecord dictionary without abstract, authors.

        """
        from bioetl.application.core.base_transformer import BaseTransformer

        silver_record = BaseTransformer.entity_to_silver_record(entity)
        silver_record.pop("abstract", None)
        silver_record.pop("authors", None)
        silver_record.pop("pmc_id", None)
        silver_record.pop("arxiv_id", None)
        return silver_record
