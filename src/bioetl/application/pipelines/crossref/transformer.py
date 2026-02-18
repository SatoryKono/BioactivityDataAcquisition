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
from bioetl.domain.normalization import extract_first_string
from bioetl.domain.services import IdentityService
from bioetl.domain.value_objects import DOI, PublicationYear

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.filtering import GoldFilterConfig, SilverFilterConfig
    from bioetl.domain.ports import (
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

    def _extract_business_data(self, record: BronzeRecord) -> dict[str, Any]:
        """Extract Publication business data from bronze record.

        Delegates field extraction to extractors module and normalization
        to DataNormalizationService per DI pattern.

        Args:
            record: Raw Bronze record from CrossRef API.

        Returns:
            Dictionary of Publication business fields.

        """
        # BronzeRecord is already a dict[str, Any]
        rec = record

        # Normalize DOI using Value Object for consistent lowercase format.
        # DOI validity is guaranteed by _pre_extract_validation, so we assert non-None.
        # If DOI were somehow invalid here, it indicates a logic error.
        doi = self.validate_value_object(DOI, rec.get("DOI"))
        assert doi is not None, "DOI should be validated in _pre_extract_validation"

        # Use extractors for structured field extraction
        journal_info = extract_journal_info(rec)
        page_info = extract_page_info(rec)
        dates = extract_dates(rec)
        content_domain = extract_content_domain(rec)
        issn_by_type = extract_issn_by_type(rec)
        published_date = extract_published_date(rec)

        # Extract and normalize authors using unified service (RULES.md §5.4)
        normalizer = self._data_normalizer

        # Extract author names and normalize (parse + serialize)
        raw_authors = extract_authors(rec)
        authors_json = normalizer.normalize_author_list(raw_authors)
        author_keys = normalizer.normalize_author_keys(raw_authors)

        # Extract author ORCID identifiers (not PII - designed for public identification)
        author_orcids = extract_author_orcids(rec)
        serialized_orcids = self.serialize_json_list(author_orcids)

        # Extract full author details with ORCID, sequence, and affiliations
        # Hash PII fields (given name, family name) while preserving non-PII data
        raw_author_details = extract_author_details(rec)
        hashed_author_details = self._hash_author_details(raw_author_details)
        serialized_author_details = self.serialize_json(hashed_author_details)

        # Extract and normalize affiliations using unified service
        affiliations_json = normalizer.normalize_affiliations(
            [
                aff
                for author in raw_author_details
                for aff in author.get("affiliations", [])
            ]
        )

        # Extract bibliographic references (not PII - public citation data)
        raw_references = extract_references(rec)
        serialized_references = self.serialize_json(raw_references)

        # Compute unified publication_date (prefer print over online)
        publication_date = self._compute_publication_date(
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
            # Fields from PublicationBaseSchema that CrossRef doesn't provide
            # (set to None to satisfy schema inheritance requirement)
            "pmid": None,
            "pmc_id": None,
            "abstract": None,
            "affiliation_list": affiliations_json,
            "title": extract_first_string(rec.get("title", [])),
            "authors": authors_json,
            "author_keys": author_keys,
            **journal_info,
            **page_info,
            **dates,
            "publication_year": self.validate_value_object(
                PublicationYear, raw_year, as_string=False
            ),
            "publication_date": publication_date,
            "publication_type": rec.get("type"),  # Raw CrossRef type
            **self._classify_publication_type("crossref", raw_type=rec.get("type")),
            "citations_received": rec.get("is-referenced-by-count"),
            "citations_made": rec.get("references-count"),
            "language": rec.get("language"),
            "license_url": extract_license_url(rec),
            "subject_keywords": self.serialize_json_list(rec.get("subject", []) or []),
            "_source": "crossref",
            # is_oa: CrossRef doesn't provide Open Access info
            "is_oa": None,
            # Lookup metadata (from adapter fallback handler)
            "_lookup_method": rec.get("_lookup_method", "doi"),
            "_original_id": rec.get("_original_id"),
            # Additional CrossRef fields
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
            # Author and reference data
            "author_orcids": serialized_orcids,
            "author_details": serialized_author_details,
            "references": serialized_references,
            # DQ flags (MUST be last, per RULES.md §2.4)
            "_dq_warn": False,
            "_dq_error": False,
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

        # Cast to str for type safety (API always returns string DOIs)
        raw_doi_str = str(raw_doi) if raw_doi else None

        # Validate DOI format using Value Object
        # This catches malformed DOIs like "invalid", "10.1234", etc.
        doi_vo = DOI.from_raw(raw_doi_str)
        if doi_vo is None:
            raise ValueError(f"Invalid DOI format: {raw_doi}")

    def _hash_author_details(
        self, author_details: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Hash PII fields in author details while preserving non-PII data.

        Author names (given, family, name) are PII and should be hashed.
        Other fields (orcid, sequence, affiliations) are not PII.

        Args:
            author_details: List of author detail dictionaries.

        Returns:
            List of author details with hashed PII fields.

        """
        hashed_details: list[dict[str, Any]] = []

        for author in author_details:
            hashed_author: dict[str, Any] = {}

            # Hash PII fields (author names)
            for pii_field in ("given", "family", "name"):
                value = author.get(pii_field)
                if value and isinstance(value, str):
                    hashed_author[pii_field] = self.hash_pii_value(value)
                else:
                    hashed_author[pii_field] = None

            # Preserve non-PII fields (orcid, sequence, authenticated_orcid, affiliations)
            # ORCID is a public persistent identifier, not PII
            hashed_author["orcid"] = author.get("orcid")
            hashed_author["authenticated_orcid"] = author.get("authenticated_orcid")
            hashed_author["sequence"] = author.get("sequence")
            hashed_author["affiliations"] = author.get("affiliations", [])

            hashed_details.append(hashed_author)

        return hashed_details

    def _compute_publication_date(
        self,
        published_print: str | None,
        published_online: str | None,
    ) -> str | None:
        """Build unified publication_date (YYYY-MM-DD), preferring print.

        Input dates from format_date_parts() are already in YYYY-MM-DD format
        (with end-of-period normalization for partial dates).

        Args:
            published_print: Print publication date (YYYY-MM-DD).
            published_online: Online publication date (YYYY-MM-DD).

        Returns:
            ISO date string (YYYY-MM-DD) or None.
        """
        return published_print or published_online

    def _should_log_fallback_lookup(self) -> bool:
        """Enable fallback lookup logging for CrossRef.

        CrossRef supports title-based fallback when DOI lookup fails (404).
        Adapter uses TitleFallbackHandler for three-phase lookup:
        1. DOI batch fetch
        2. Title fallback for unresolved DOIs
        3. Title-only lookup for entries without DOIs

        Returns:
            True - log fallback lookups for observability.

        """
        return True

        # Any: accepts any dataclass ...

    def entity_to_silver_record(self, entity: Any) -> dict[str, Any]:
        """Convert Domain Entity to SilverRecord, preserving base schema fields.

        Overrides base implementation to handle ISSN list conversion.
        Note: Fields like pmid, pmc_id, abstract, affiliation_list are kept
        with None values to satisfy PublicationBaseSchema inheritance requirement.

        Args:
            entity: Domain entity (dataclass).

        Returns:
            SilverRecord dictionary with all base schema fields.

        """
        # Get base silver record
        silver_record = super().entity_to_silver_record(entity)

        # Note: Do NOT remove pmid, pmc_id, abstract, affiliation_list
        # These fields inherit from PublicationBaseSchema and must exist in DataFrame
        # even if set to None (Pandera requires columns to exist, not just be nullable)

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
