"""CrossRef Transformer.

Transforms Bronze records to Silver format (Work entity inflation).
Contains orchestration logic for CrossRef data transformation per Hexagonal Architecture.

This module was refactored from infrastructure/adapters/crossref/mappers.py
to properly separate business logic from infrastructure concerns.

Note: Business logic functions are delegated to domain layer per REFACTOR-004.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, cast

from bioetl.application.core.base_transformer import BaseTransformer
from bioetl.domain.entities.crossref import CROSSREF_TYPE_MAP, Work
from bioetl.domain.normalization import (
    extract_first_string,
    format_date_parts,
    normalize_doi,
    parse_page_range,
    strip_html_tags,
)
from bioetl.domain.transformations import generate_entity_id
from bioetl.domain.validation import validate_year_range

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.filtering import GoldFilterConfig
    from bioetl.domain.ports import MetricsPort, TracingPort
    from bioetl.domain.types import BronzeRecord, SilverRecord


class CrossRefTransformer(BaseTransformer):
    """Transforms CrossRef bronze records to silver.

    Implements field extraction, normalization, and type coercion
    according to the CrossRef → Work entity mapping specification.

    Subclasses BaseTransformer to provide:
    - Unified error handling via Template Method
    - Content hash computation
    - Tracing and metrics observability (O1)
    """

    def __init__(
        self,
        provider: str = "crossref",
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
        gold_filters: GoldFilterConfig | None = None,
    ) -> None:
        """Initialize CrossRef transformer.

        Args:
            provider: Data provider identifier. Defaults to 'crossref'.
            tracer: Optional tracing port for distributed tracing.
            metrics: Optional metrics port for duration/error tracking.
            gold_filters: Optional filter configuration for Gold layer.

        """
        super().__init__(
            provider, entity_type="work", tracer=tracer, metrics=metrics, gold_filters=gold_filters
        )

    # ========================================================================
    # Field Extraction Methods (Orchestration - delegates to domain)
    # ========================================================================

    @staticmethod
    def _extract_authors(work: Mapping[str, Any]) -> list[str]:
        """Extract author names in 'given family' format.

        This is CrossRef-specific extraction logic (not generic normalization).

        Args:
            work: CrossRef work record.

        Returns:
            List of author names.

        """
        authors = []
        for author in work.get("author", []):
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
    def _extract_year(work: Mapping[str, Any]) -> int | None:
        """Extract publication year from date-parts.

        Tries published-print, then published-online, then issued.
        Delegates validation to domain.validation.validate_year_range.

        Args:
            work: CrossRef work record.

        Returns:
            Publication year or None.

        """
        for date_field in ["published-print", "published-online", "issued"]:
            date_info = work.get(date_field, {})
            date_parts = date_info.get("date-parts", [[]])
            if date_parts and date_parts[0] and len(date_parts[0]) > 0:
                year = date_parts[0][0]
                if isinstance(year, int) and validate_year_range(year):
                    return year
        return None

    @staticmethod
    def _extract_license_url(work: Mapping[str, Any]) -> str | None:
        """Extract license URL from work.

        Args:
            work: CrossRef work record.

        Returns:
            First license URL or None.

        """
        licenses = work.get("license", [])
        if licenses and len(licenses) > 0:
            url: str | None = licenses[0].get("URL")
            return url
        return None

    # ========================================================================
    # Main Transformation
    # ========================================================================

    def _extract_business_data(self, record: BronzeRecord) -> dict[str, Any]:
        """Extract Work business data from bronze record.

        Delegates normalization to domain layer per REFACTOR-004.

        Args:
            record: Raw Bronze record from CrossRef API.

        Returns:
            Dictionary of Work business fields.

        """
        # Use domain functions for normalization (cast from BronzeRecord to dict)
        data = cast("dict[str, Any]", record)
        doi = normalize_doi(cast("str | None", data.get("DOI", ""))) or ""
        first_page, last_page = parse_page_range(cast("str | None", data.get("page")))

        # Extract date fields using domain functions
        published_print = data.get("published-print", {})
        published_online = data.get("published-online", {})

        # Extract abstract with HTML stripping via domain function
        abstract_raw = cast("str | None", data.get("abstract", ""))
        abstract = strip_html_tags(abstract_raw) if abstract_raw else None

        return {
            "doi": doi,
            "title": extract_first_string(cast("list[str] | None", data.get("title", []))),
            "abstract": abstract,
            "authors": self._extract_authors(data),
            "journal": extract_first_string(cast("list[str] | None", data.get("container-title", []))),
            "issn": data.get("ISSN", []),
            "publisher": data.get("publisher"),
            "volume": data.get("volume"),
            "issue": data.get("issue"),
            "first_page": first_page,
            "last_page": last_page,
            "year": self._extract_year(data),
            "published_print": format_date_parts(
                published_print.get("date-parts") if isinstance(published_print, dict) else None
            ),
            "published_online": format_date_parts(
                published_online.get("date-parts") if isinstance(published_online, dict) else None
            ),
            "doc_type": CROSSREF_TYPE_MAP.get(cast("str", data.get("type", "")), "PUBLICATION"),
            "citation_count": data.get("is-referenced-by-count"),
            "reference_count": data.get("references-count"),
            "language": data.get("language"),
            "license_url": self._extract_license_url(data),
            "subjects": data.get("subject", []),
            "source": "crossref",
        }

    async def _transform_impl(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> SilverRecord | None:
        """Transform CrossRef bronze record to silver format.

        Args:
            context: Pipeline context with run_id, run_type, logger.
            record: Raw Bronze record from CrossRef API.
            index: Sequential index of the record in the pipeline run.

        Returns:
            SilverRecord if transformation successful, None if skipped.

        """
        # 1. Validate required field
        doi = record.get("DOI")
        if not doi:
            raise ValueError("DOI is required for CrossRef Work")

        # 2. Extract business data
        business_data = self._extract_business_data(record)

        # 3. Generate entity ID (normalized DOI)
        entity_id = generate_entity_id(
            record={"doi": business_data["doi"]},
            provider=self.provider,
            id_field="doi",
        )

        # 4. Compute content hash
        content_hash = self.compute_content_hash(business_data, exclude_none=True)

        # 5. Create domain entity
        entity = self._create_entity(
            Work,
            context,
            entity_id=entity_id,
            content_hash=content_hash,
            index=index,
            **business_data,
        )

        # 6. Convert to SilverRecord
        return cast("SilverRecord", self.entity_to_silver_record(entity))
