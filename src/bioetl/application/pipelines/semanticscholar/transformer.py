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
    extract_author_orcids,
    extract_author_s2_ids,
    extract_citation_contexts,
    extract_external_ids,
    extract_fields_of_study,
    extract_journal_info,
    extract_open_access_info,
    extract_tldr,
)
from bioetl.domain.entities.semanticscholar import SemanticScholarPublicationEntity
from bioetl.domain.value_objects import DOI, PublicationYear, PubMedId

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
    - abstract: abstract (fallback to tldr.text if missing)
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
    - subject_fields: fieldsOfStudy
    - publication_type: publicationTypes joined by "|"
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

    def _resolve_publication_type(self, publication_types: Any) -> str:
        """Resolve raw publication types list to a unified scalar string."""
        if not isinstance(publication_types, list):
            return "PUBLICATION"
        cleaned = [
            str(item).strip()
            for item in publication_types
            if item is not None and str(item).strip()
        ]
        return "|".join(cleaned) if cleaned else "PUBLICATION"

    def _extract_validated_ids(self, rec: dict[str, Any]) -> dict[str, Any]:
        """Extract and validate external identifiers using Value Objects."""
        external_ids = extract_external_ids(rec.get("externalIds"))
        doi_vo = DOI.from_raw(external_ids.get("doi"))
        pmid_vo = PubMedId.from_raw(external_ids.get("pmid"))
        return {
            "paper_id": rec.get("paperId"),
            "doi": str(doi_vo) if doi_vo else None,
            "pmid": str(pmid_vo) if pmid_vo else None,
            "dblp_id": external_ids.get("dblp"),
            "corpus_id": external_ids.get("corpus_id"),
        }

    def _extract_author_metadata(self, authors_list: Any) -> dict[str, Any]:
        """Extract author identifiers, h-indices, and affiliations."""
        author_s2_ids = extract_author_s2_ids(authors_list)
        author_orcids = extract_author_orcids(authors_list)
        author_h_indices = extract_author_h_indices(authors_list)
        affiliations = extract_affiliations(authors_list)
        return {
            "author_s2_ids": self.serialize_json_list(author_s2_ids)
            if author_s2_ids
            else None,
            "author_orcids": self.serialize_json_list(author_orcids)
            if any(author_orcids)
            else None,
            "author_h_indices": self.serialize_json_list(author_h_indices)
            if any(h is not None for h in author_h_indices)
            else None,
            "affiliation_list": self.serialize_json_list(affiliations)
            if affiliations
            else None,
        }

    def _extract_business_data(self, record: BronzeRecord) -> dict[str, Any]:
        """Extract and normalize fields from Semantic Scholar record.

        Args:
            record: Raw Bronze record from Semantic Scholar API.

        Returns:
            Dictionary of extracted and normalized fields.

        """
        rec = cast("dict[str, Any]", record)

        ids = self._extract_validated_ids(rec)
        author_meta = self._extract_author_metadata(rec.get("authors"))

        citation_contexts = extract_citation_contexts(rec.get("citations"))
        journal_info = extract_journal_info(rec.get("journal"), rec.get("venue"))
        oa_info = extract_open_access_info(
            rec.get("isOpenAccess"), rec.get("openAccessPdf")
        )

        tldr = self._data_normalizer.normalize_string(extract_tldr(rec.get("tldr")))
        abstract = self._data_normalizer.normalize_string(rec.get("abstract"))
        if abstract is None:
            abstract = tldr

        publication_types = rec.get("publicationTypes")

        return {
            **ids,
            "title": rec.get("title"),
            "abstract": abstract,
            "tldr": tldr,
            **author_meta,
            "citation_contexts": self.serialize_json_list(citation_contexts)
            if citation_contexts
            else None,
            "journal": journal_info.get("journal"),
            "volume": journal_info.get("volume"),
            "issue": journal_info.get("issue"),
            "page_range": journal_info.get("page_range"),
            "page_first": journal_info.get("page_first"),
            "page_last": journal_info.get("page_last"),
            "publication_year": self.validate_value_object(
                PublicationYear, rec.get("year"), as_string=False
            ),
            "publication_date": self._normalize_partial_date(
                rec.get("publicationDate")
            ),
            "citations_received": rec.get("citationCount"),
            "citations_made": rec.get("referenceCount"),
            "influential_citation_count": rec.get("influentialCitationCount"),
            "is_oa": oa_info.get("is_oa"),
            "open_access_url": oa_info.get("url"),
            "oa_status": oa_info.get("oa_status"),
            "subject_fields": self.serialize_json(
                extract_fields_of_study(rec.get("fieldsOfStudy"))
            ),
            "publication_type": self._resolve_publication_type(publication_types),
            **self._classify_publication_type(
                "semanticscholar",
                raw_types_list=[
                    str(t).strip()
                    for t in publication_types
                    if t is not None and str(t).strip()
                ]
                if isinstance(publication_types, list)
                else None,
            ),
            "publication_types": self.serialize_json(publication_types),
            "_source": "semanticscholar",
            "_lookup_method": rec.get("_lookup_method", "unknown"),
            "_original_id": rec.get("_original_id"),
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
            SilverRecord dictionary without pmc_id/arxiv_id.

        """
        from bioetl.application.core.base_transformer import BaseTransformer

        silver_record = BaseTransformer.entity_to_silver_record(entity)
        silver_record.pop("pmc_id", None)
        silver_record.pop("arxiv_id", None)
        return silver_record
