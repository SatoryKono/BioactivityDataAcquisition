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

from typing import TYPE_CHECKING, Any, cast

from bioetl.application.pipelines.common import BasePublicationTransformer
from bioetl.domain.entities.crossref import CROSSREF_TYPE_MAP, PublicationEntity
from bioetl.domain.normalization import (
    extract_first_string,
    parse_page_range,
)
from bioetl.domain.services import DataNormalizationService, IdentityService
from bioetl.domain.validation import validate_year_range

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.filtering import GoldFilterConfig
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
            gold_filters=gold_filters,
            identity_service=identity_service,
            pii_hasher=pii_hasher,
        )
        self._data_normalizer = data_normalizer or DataNormalizationService()

    # ========================================================================
    # Field Extraction Methods (Orchestration - delegates to domain)
    # ========================================================================

    @staticmethod
    def _extract_authors(publication: dict[str, Any]) -> list[str]:
        """Extract author names in 'given family' format.

        This is CrossRef-specific extraction logic (not generic normalization).

        Args:
            publication: CrossRef publication record.

        Returns:
            List of author names.

        """
        authors = []
        for author in publication.get("author", []):
            given = author.get("given", "").strip()
            family = author.get("family", "").strip()
            if given and family:
                authors.append(f"{given} {family}")
            elif family:
                authors.append(family)
            elif given:
                authors.append(given)
        return authors

    @staticmethod
    def _extract_year(publication: dict[str, Any]) -> int | None:
        """Extract publication year from date-parts.

        Tries published-print, then published-online, then issued.
        Delegates validation to domain.validation.validate_year_range.

        Args:
            publication: CrossRef publication record.

        Returns:
            Publication year or None.

        """
        for date_field in ["published-print", "published-online", "issued"]:
            date_info = publication.get(date_field, {})
            date_parts = date_info.get("date-parts", [[]])
            if date_parts and date_parts[0] and len(date_parts[0]) > 0:
                year = date_parts[0][0]
                if isinstance(year, int) and validate_year_range(year):
                    return year
        return None

    @staticmethod
    def _extract_license_url(publication: dict[str, Any]) -> str | None:
        """Extract license URL from publication.

        Args:
            publication: CrossRef publication record.

        Returns:
            First license URL or None.

        """
        licenses = publication.get("license", [])
        if licenses and len(licenses) > 0:
            url: str | None = licenses[0].get("URL")
            return url
        return None

    # ========================================================================
    # Main Transformation
    # ========================================================================

    def _extract_business_data(self, record: BronzeRecord) -> dict[str, Any]:
        """Extract Publication business data from bronze record.

        Delegates normalization to DataNormalizationService per DI pattern.

        Args:
            record: Raw Bronze record from CrossRef API.

        Returns:
            Dictionary of Publication business fields.

        """
        # Cast to dict for type-safe access (BronzeRecord is an empty TypedDict marker)
        rec = cast("dict[str, Any]", record)

        # Use DataNormalizationService for normalization
        normalizer = self._data_normalizer
        doi = normalizer.normalize_doi(rec.get("DOI", "")) or ""
        first_page, last_page = parse_page_range(rec.get("page"))

        # Extract date fields using normalizer service
        published_print = rec.get("published-print", {})
        published_online = rec.get("published-online", {})

        # Extract abstract with HTML stripping via normalizer service
        abstract_raw = rec.get("abstract", "")
        abstract = normalizer.strip_html_tags(abstract_raw) if abstract_raw else None

        # Extract and hash PII fields (RULES.md §5.4)
        # Authors stored as JSON-serialized list for unified format across providers
        raw_authors = self._extract_authors(rec)
        hashed_authors = self.hash_pii_list(raw_authors) or []

        return {
            "doi": doi,
            "title": extract_first_string(rec.get("title", [])),
            "abstract": abstract,
            "authors": self.serialize_json_list(hashed_authors),
            "journal": extract_first_string(rec.get("container-title", [])),
            "issn": rec.get("ISSN", []),
            "publisher": rec.get("publisher"),
            "volume": rec.get("volume"),
            "issue": rec.get("issue"),
            "first_page": first_page,
            "last_page": last_page,
            "year": self._extract_year(rec),
            "published_print": normalizer.format_date_parts(
                published_print.get("date-parts")
                if isinstance(published_print, dict)
                else None
            ),
            "published_online": normalizer.format_date_parts(
                published_online.get("date-parts")
                if isinstance(published_online, dict)
                else None
            ),
            "doc_type": CROSSREF_TYPE_MAP.get(rec.get("type", ""), "PUBLICATION"),
            "citation_count": rec.get("is-referenced-by-count"),
            "reference_count": rec.get("references-count"),
            "language": rec.get("language"),
            "license_url": self._extract_license_url(rec),
            "subjects": rec.get("subject", []),
            "source": "crossref",
        }

    def _get_primary_id_field(self) -> str:
        """Return the primary ID field name for CrossRef publications.

        Returns:
            'doi' - the CrossRef-specific identifier field.

        """
        return "doi"

    def _get_entity_class(self) -> type[PublicationEntity]:
        """Return the domain entity class for CrossRef publications.

        Returns:
            PublicationEntity class.

        """
        return PublicationEntity

    def _pre_extract_validation(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> None:
        """Validate DOI exists before extraction.

        CrossRef publications require DOI as mandatory identifier.
        Raises ValueError (caught by BaseTransformer.transform).

        Args:
            context: Pipeline context (unused).
            record: Raw Bronze record from CrossRef API.
            index: Sequential index (unused).

        Raises:
            ValueError: If DOI field is missing or empty.

        """
        doi = record.get("DOI")
        if not doi:
            raise ValueError("DOI is required for CrossRef Publication")

    def _should_log_fallback_lookup(self) -> bool:
        """Disable fallback lookup logging for CrossRef.

        CrossRef uses DOI-only lookup without title fallback mechanism.

        Returns:
            False - no fallback logging needed.

        """
        return False
