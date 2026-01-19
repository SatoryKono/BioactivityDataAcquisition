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
from bioetl.application.pipelines.crossref.extractors import (
    extract_authors,
    extract_dates,
    extract_journal_info,
    extract_license_url,
    extract_page_info,
    extract_year,
)
from bioetl.domain.entities.crossref import CROSSREF_TYPE_MAP, CrossRefPublicationEntity
from bioetl.domain.normalization import extract_first_string
from bioetl.domain.services import IdentityService
from bioetl.domain.value_objects import DOI

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
        # Cast to dict for type-safe access (BronzeRecord is an empty TypedDict marker)
        rec = cast("dict[str, Any]", record)

        # Validate DOI using Value Object (returns None for invalid/empty)
        # CrossRef always provides DOI, so we use empty string as fallback for type consistency
        doi_vo = DOI.from_raw(rec.get("DOI"))
        doi = str(doi_vo) if doi_vo else ""

        # Use extractors for structured field extraction
        journal_info = extract_journal_info(rec)
        page_info = extract_page_info(rec)
        dates = extract_dates(rec)

        # Extract abstract with HTML stripping via normalizer service
        normalizer = self._data_normalizer
        abstract_raw = rec.get("abstract", "")
        abstract = normalizer.strip_html_tags(abstract_raw) if abstract_raw else None

        # Extract and hash PII fields (RULES.md §5.4)
        # Authors stored as JSON-serialized list for unified format across providers
        raw_authors = extract_authors(rec)
        hashed_authors = self.hash_pii_list(raw_authors) or []

        return {
            "doi": doi,
            "title": extract_first_string(rec.get("title", [])),
            "abstract": abstract,
            "authors": self.serialize_json_list(hashed_authors),
            **journal_info,
            **page_info,
            **dates,
            "year": extract_year(rec),
            "doc_type": CROSSREF_TYPE_MAP.get(rec.get("type", ""), "PUBLICATION"),
            "citation_count": rec.get("is-referenced-by-count"),
            "reference_count": rec.get("references-count"),
            "language": rec.get("language"),
            "license_url": extract_license_url(rec),
            "subjects": rec.get("subject", []),
            "source": "crossref",
            # Lookup metadata (from adapter fallback handler)
            "_lookup_method": rec.get("_lookup_method", "doi"),
            "_original_id": rec.get("_original_id"),
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
