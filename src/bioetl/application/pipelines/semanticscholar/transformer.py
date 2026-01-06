# src/bioetl/application/pipelines/semanticscholar/transformer.py
"""Semantic Scholar Publication Transformer.

Transforms Bronze records to Silver format (Publication entity).
Handles both DOI-resolved and title-fallback records.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from bioetl.application.core.base_transformer import BaseTransformer
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

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.filtering import GoldFilterConfig
    from bioetl.domain.ports import MetricsPort, PiiHasherPort, TracingPort
    from bioetl.domain.services import IdentityService
    from bioetl.domain.types import BronzeRecord, SilverRecord


class SemanticScholarPublicationTransformer(BaseTransformer):
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
    - is_open_access: isOpenAccess
    - open_access_url: openAccessPdf.url
    - fields_of_study: fieldsOfStudy
    - publication_types: publicationTypes

    Handles lookup metadata:
    - _lookup_method: "doi" | "title_fallback" | "title_only"
    - _original_doi: Original DOI for fallback records

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
            "abstract": rec.get("abstract"),
            "tldr": tldr,
            "authors": self.serialize_json(hashed_authors),
            "journal": journal_info.get("journal_name"),
            "volume": journal_info.get("volume"),
            "pages": journal_info.get("pages"),
            "venue": rec.get("venue"),
            "year": year,
            "publication_date": rec.get("publicationDate"),
            "citation_count": rec.get("citationCount"),
            "reference_count": rec.get("referenceCount"),
            "is_open_access": oa_info.get("is_open_access"),
            "open_access_url": oa_info.get("url"),
            "open_access_status": oa_info.get("status"),
            "fields_of_study": self.serialize_json(fields_of_study),
            "publication_types": self.serialize_json(rec.get("publicationTypes")),
            "source": "semanticscholar",
            # Lookup metadata
            "_lookup_method": lookup_method,
            "_original_doi": original_doi,
        }

    async def _transform_impl(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> SilverRecord | None:
        """Transform Semantic Scholar record to Silver format.

        Args:
            context: Pipeline context with run_id, run_type, logger.
            record: Raw Bronze record from Semantic Scholar API.
            index: Sequential index of the record in the pipeline run.

        Returns:
            SilverRecord if transformation successful, None if record should be skipped.

        """
        # 1. Extract business data
        business_data = self._extract_business_data(record)

        # 2. Validate required field
        paper_id = business_data.get("paper_id")
        if not paper_id:
            context.logger.warning(
                "record_skipped_no_id",
                index=index,
                lookup_method=business_data.get("_lookup_method"),
            )
            return None

        # 3. Log fallback usage for metrics
        lookup_method = business_data.get("_lookup_method", "unknown")
        if lookup_method in ("title_fallback", "title_only"):
            context.logger.info(
                "fallback_lookup_used",
                paper_id=paper_id,
                lookup_method=lookup_method,
                original_doi=business_data.get("_original_doi"),
            )

        # 4. Generate entity ID using IdentityService
        entity_id = self.compute_entity_id(
            source_id=paper_id,
            record={"paper_id": paper_id},
        )

        # 5. Compute content hash (exclude lookup metadata from hash)
        hash_data = {
            k: v
            for k, v in business_data.items()
            if not k.startswith("_")  # Exclude _lookup_method, _original_doi
        }
        content_hash = self.compute_content_hash(hash_data, exclude_none=True)

        # 6. Create domain entity
        entity = self._create_entity(
            SemanticScholarPublicationEntity,
            context,
            entity_id=entity_id,
            content_hash=content_hash,
            index=index,
            **business_data,
        )

        # 7. Convert to SilverRecord
        return cast("SilverRecord", self.entity_to_silver_record(entity))
