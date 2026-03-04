"""CrossRef Transformer.

Transforms Bronze records to Silver format (Publication entity inflation).
Contains orchestration logic for CrossRef data transformation per Hexagonal Architecture.

This module was refactored from infrastructure/adapters/crossref/mappers.py
to properly separate business logic from infrastructure concerns.

Terminology:
- Uses "Publication" instead of CrossRef API term "Work" for Ubiquitous Language
- All layers use "publication" to refer to scholarly works (articles, preprints, etc.)

Note: Business logic functions are delegated to domain layer per REFACTOR-004.
Uses DataNormalizationService for text normalization (DI pattern).
"""

from __future__ import annotations

__all__ = ["CrossRefPublicationTransformer"]


from typing import TYPE_CHECKING, Any

from bioetl.application.pipelines.common import BasePublicationTransformer
from bioetl.application.pipelines.crossref.extractors import (
    extract_author_details,
    extract_author_orcids,
    extract_authors,
    extract_content_domain,
    extract_dates,
    extract_issn_by_type,
    extract_journal_info,
    extract_license_url,
    extract_page_info,
    extract_published_date,
    extract_references,
)
from bioetl.domain.entities.crossref import CrossRefPublicationEntity
from bioetl.domain.mapping.publication_type_mapping import normalize_publication_type
from bioetl.domain.normalization import extract_first_string
from bioetl.domain.services import IdentityService
from bioetl.domain.types import GoldRecord
from bioetl.domain.value_objects import DOI

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.filtering import GoldFilterConfig, SilverFilterConfig
    from bioetl.domain.ports import (
        ContractPolicyPort,
        DataNormalizationPort,
        MetricsPort,
        PiiHasherPort,
        TracingPort,
    )
    from bioetl.domain.types import BronzeRecord


class CrossRefPublicationTransformer(BasePublicationTransformer):
    """Transforms CrossRef bronze records to silver.

    Implements field extraction, normalization, and type coercion
    according to the CrossRef → Publication entity mapping specification.

    Subclasses BasePublicationTransformer to provide:
    - Unified transformation flow via Template Method
    - Pre-extraction DOI validation (raises ValueError if missing)
    - Content hash computation
    - Tracing and metrics observability (O1)

    Note: Disables fallback logging since CrossRef uses DOI-only lookup.
    """

    def __init__(
        self,
        provider: str = "crossref",
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
        """Initialize CrossRef transformer.

        Args:
            provider: Data provider identifier. Defaults to 'crossref'.
            entity_type: Entity type for metrics labels. Defaults to 'publication'.
            tracer: Optional tracing port for distributed tracing.
            metrics: Optional metrics port for duration/error tracking.
            silver_filters: Optional filter configuration for Silver layer.
            gold_filters: Optional filter configuration for Gold layer.
            identity_service: Service for computing entity IDs and content hashes.
            pii_hasher: Optional PII hasher for hashing author names (RULES.md §5.4).
            data_normalizer: Optional data normalization service for text normalization.
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

    def _extract_business_data(self, record: BronzeRecord) -> GoldRecord:
        """Extract Publication business data from bronze record.

        Delegates field extraction to extractors module and normalization
        to DataNormalizationService per DI pattern.

        Args:
            record: Raw Bronze record from CrossRef API.

        Returns:
            Dictionary of Publication business fields.

        """
        # BronzeRecord is already a JsonDict
        rec = record

        # Normalize DOI using Value Object for consistent lowercase format.
        doi = self._validate_doi(rec.get("DOI"))
        assert doi is not None, "DOI should be validated in _pre_extract_validation"

        # Use extractors for structured field extraction
        journal_info = extract_journal_info(rec)
        page_info = extract_page_info(rec)
        dates = extract_dates(rec)
        content_domain = extract_content_domain(rec)
        issn_by_type = extract_issn_by_type(rec)
        published_date = extract_published_date(rec)

        # Extract and normalize authors using mixin (RULES.md §5.4)
        raw_authors = extract_authors(rec)
        author_block = self._normalize_author_block(
            raw_authors,
            raw_affiliations=[
                aff
                for author in extract_author_details(rec)
                for aff in author.get("affiliations", [])
            ],
        )

        # Extract author ORCID identifiers (not PII - designed for public identification)
        author_orcids = extract_author_orcids(rec)
        serialized_orcids = self.serialize_json_list(author_orcids)

        # Hash PII in author details using mixin
        raw_author_details = extract_author_details(rec)
        hashed_author_details = self._hash_author_pii_details(raw_author_details)
        serialized_author_details = self.serialize_json(hashed_author_details)

        # Extract bibliographic references (not PII - public citation data)
        raw_references = extract_references(rec)
        serialized_references = self.serialize_json(raw_references)

        # Compute unified publication_date using mixin (prefer print over online)
        publication_date = self._prefer_date(
            dates.get("published_print"),
            dates.get("published_online"),
        )

        # Extract raw year from date-parts for validation
        raw_year = None
        for date_field in ["published-print", "published-online", "issued"]:
            date_info = rec.get(date_field, {})
            date_parts = date_info.get("date-parts", [[]])
            if date_parts and date_parts[0] and len(date_parts[0]) > 0:
                raw_year = date_parts[0][0]
                break

        return {
            "doi": doi,
            "pmid": None,
            "pmc_id": None,
            "abstract": None,
            "affiliation_list": author_block.get("affiliation_list"),
            "title": extract_first_string(rec.get("title", [])),
            "authors": author_block["authors"],
            "author_keys": author_block["author_keys"],
            **journal_info,
            **page_info,
            **dates,
            "publication_year": self._validate_publication_year(raw_year),
            "publication_date": publication_date,
            "publication_type": normalize_publication_type(rec.get("type")),
            **self._classify_publication_type("crossref", raw_type=rec.get("type")),
            "citations_received": rec.get("is-referenced-by-count"),
            "citations_made": rec.get("references-count"),
            "language": rec.get("language"),
            "license_url": extract_license_url(rec),
            "subject_keywords": self.serialize_json_list(rec.get("subject", []) or []),
            "is_oa": None,
            "alternative_id": self.serialize_json_list(
                rec.get("alternative-id", []) or []
            ),
            "journal_name_short": extract_first_string(
                rec.get("short-container-title")
            ),
            "published": published_date,
            "content_domain_domains": self.serialize_json_list(
                content_domain.get("content_domain_domains", [])
            ),
            "content_domain_crossmark_restriction": content_domain.get(
                "content_domain_crossmark_restriction"
            ),
            **issn_by_type,
            "author_orcids": serialized_orcids,
            "author_details": serialized_author_details,
            "references": serialized_references,
            **self._build_metadata_block("crossref", rec, default_lookup="doi"),
        }

    def _get_primary_id_field(self) -> str:
        """Return the primary ID field name for CrossRef publications.

        Returns:
            'doi' - the CrossRef-specific identifier field.

        """
        return "doi"

    def _get_entity_class(self) -> type[CrossRefPublicationEntity]:
        """Return the domain entity class for CrossRef publications.

        Returns:
            CrossRefPublicationEntity class.

        """
        return CrossRefPublicationEntity

    def _pre_extract_validation(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> None:
        """Validate DOI exists and is well-formed before extraction.

        CrossRef publications require DOI as mandatory identifier.
        Both missing and malformed DOIs result in record rejection,
        as DOI is the primary identifier for entity_id computation.

        Raises ValueError (caught by BaseTransformer.transform).

        Args:
            context: Pipeline context (unused).
            record: Raw Bronze record from CrossRef API.
            index: Sequential index (unused).

        Raises:
            ValueError: If DOI field is missing, empty, or malformed.

        """
        raw_doi = record.get("DOI")
        if not raw_doi:
            raise ValueError("DOI is required for CrossRef Publication")

        raw_doi_str = str(raw_doi) if raw_doi else None

        doi_vo = DOI.from_raw(raw_doi_str)
        if doi_vo is None:
            raise ValueError(f"Invalid DOI format: {raw_doi}")

    def _should_log_fallback_lookup(self) -> bool:
        """Enable fallback lookup logging for CrossRef.

        CrossRef supports title-based fallback when DOI lookup fails (404).

        Returns:
            True - log fallback lookups for observability.

        """
        return True

    def entity_to_silver_record(
        self,
        entity: Any,  # Any: domain entity dataclass; concrete type varies by pipeline subclass
    ) -> GoldRecord:
        """Convert Domain Entity to SilverRecord, preserving base schema fields.

        Overrides base implementation to handle ISSN list conversion.

        Args:
            entity: Domain entity (dataclass).

        Returns:
            SilverRecord dictionary with all base schema fields.

        """
        silver_record = super().entity_to_silver_record(entity)

        # Convert ISSN list to scalar + JSON array (unification with other providers)
        issn_raw = silver_record.get("issn")
        if isinstance(issn_raw, list):
            silver_record["issn"] = issn_raw[0] if issn_raw else None
            silver_record["issn_list"] = (
                self.serialize_json_list(issn_raw) if issn_raw else None
            )
        else:
            silver_record.setdefault("issn_list", None)

        return silver_record
