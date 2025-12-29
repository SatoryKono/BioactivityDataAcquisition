"""CrossRef Transformer.

Transforms Bronze records to Silver format (Work entity inflation).
Contains business logic for CrossRef data transformation per Hexagonal Architecture.

This module was refactored from infrastructure/adapters/crossref/mappers.py
to properly separate business logic from infrastructure concerns.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, cast

from bioetl.application.core.base_transformer import BaseTransformer
from bioetl.domain.entities.crossref import CROSSREF_TYPE_MAP, Work
from bioetl.domain.transformations import generate_entity_id

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.filtering import GoldFilterConfig
    from bioetl.domain.ports import MetricsPort, TracingPort
    from bioetl.domain.types import BronzeRecord, SilverRecord


# HTML tag pattern for stripping from abstract
_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")


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
    # Field Extraction Methods (Business Logic)
    # ========================================================================

    @staticmethod
    def normalize_doi(doi: str) -> str:
        """Normalize DOI to lowercase, stripped format.

        Args:
            doi: Raw DOI string from API.

        Returns:
            Normalized DOI (lowercase, stripped).

        """
        return doi.strip().lower()

    @staticmethod
    def extract_title(work: dict[str, Any]) -> str | None:
        """Extract first title from work response.

        Args:
            work: CrossRef work record.

        Returns:
            First title or None.

        """
        titles = work.get("title", [])
        if titles and len(titles) > 0:
            return str(titles[0]).strip()
        return None

    @staticmethod
    def extract_authors(work: dict[str, Any]) -> list[str]:
        """Extract author names in 'given family' format.

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
    def extract_journal(work: dict[str, Any]) -> str | None:
        """Extract journal name from container-title.

        Args:
            work: CrossRef work record.

        Returns:
            First container title or None.

        """
        container = work.get("container-title", [])
        if container and len(container) > 0:
            return str(container[0]).strip()
        return None

    @staticmethod
    def extract_year(work: dict[str, Any]) -> int | None:
        """Extract publication year from date-parts.

        Tries published-print, then published-online, then issued.

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
                if isinstance(year, int) and 1800 <= year <= 2100:
                    return year
        return None

    @staticmethod
    def format_date_parts(date_parts: list[list[int]] | None) -> str | None:
        """Format date-parts to ISO date string.

        Args:
            date_parts: CrossRef date-parts array [[year, month, day]].

        Returns:
            ISO date string (YYYY-MM-DD, YYYY-MM, or YYYY).

        """
        if not date_parts or not date_parts[0]:
            return None

        parts = date_parts[0]
        if len(parts) >= 3:
            return f"{parts[0]:04d}-{parts[1]:02d}-{parts[2]:02d}"
        elif len(parts) >= 2:
            return f"{parts[0]:04d}-{parts[1]:02d}"
        elif len(parts) >= 1:
            return f"{parts[0]:04d}"
        return None

    @staticmethod
    def extract_pages(work: dict[str, Any]) -> tuple[str | None, str | None]:
        """Extract first and last page from page field.

        Args:
            work: CrossRef work record.

        Returns:
            Tuple of (first_page, last_page).

        """
        page = work.get("page", "")
        if not page:
            return None, None

        if "-" in page:
            parts = page.split("-", 1)
            first = parts[0].strip() or None
            last = parts[1].strip() if len(parts) > 1 else None
            return first, last
        return page.strip() or None, None

    @staticmethod
    def strip_html_tags(text: str) -> str:
        """Strip HTML tags from abstract text.

        Args:
            text: Abstract text potentially containing HTML.

        Returns:
            Plain text with HTML tags removed.

        """
        return _HTML_TAG_PATTERN.sub("", text).strip()

    @staticmethod
    def extract_abstract(work: dict[str, Any]) -> str | None:
        """Extract and clean abstract text.

        Args:
            work: CrossRef work record.

        Returns:
            Clean abstract text or None.

        """
        abstract = work.get("abstract", "")
        if not abstract:
            return None
        return CrossRefTransformer.strip_html_tags(abstract) or None

    @staticmethod
    def map_doc_type(crossref_type: str) -> str:
        """Map CrossRef type to internal document type.

        Args:
            crossref_type: CrossRef work type.

        Returns:
            Internal document type (PUBLICATION or PREPRINT).

        """
        return CROSSREF_TYPE_MAP.get(crossref_type, "PUBLICATION")

    @staticmethod
    def extract_issn(work: dict[str, Any]) -> list[str]:
        """Extract ISSN list from work.

        Args:
            work: CrossRef work record.

        Returns:
            List of ISSNs.

        """
        issns: list[str] = work.get("ISSN", [])
        return issns

    @staticmethod
    def extract_license_url(work: dict[str, Any]) -> str | None:
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

    @staticmethod
    def extract_subjects(work: dict[str, Any]) -> list[str]:
        """Extract subject areas from work.

        Args:
            work: CrossRef work record.

        Returns:
            List of subject areas.

        """
        subjects: list[str] = work.get("subject", [])
        return subjects

    # ========================================================================
    # Main Transformation
    # ========================================================================

    def _extract_business_data(self, record: BronzeRecord) -> dict[str, Any]:
        """Extract Work business data from bronze record.

        Args:
            record: Raw Bronze record from CrossRef API.

        Returns:
            Dictionary of Work business fields.

        """
        doi = self.normalize_doi(record.get("DOI", ""))
        first_page, last_page = self.extract_pages(record)

        # Extract date fields
        published_print = record.get("published-print", {})
        published_online = record.get("published-online", {})

        return {
            "doi": doi,
            "title": self.extract_title(record),
            "abstract": self.extract_abstract(record),
            "authors": self.extract_authors(record),
            "journal": self.extract_journal(record),
            "issn": self.extract_issn(record),
            "publisher": record.get("publisher"),
            "volume": record.get("volume"),
            "issue": record.get("issue"),
            "first_page": first_page,
            "last_page": last_page,
            "year": self.extract_year(record),
            "published_print": self.format_date_parts(
                published_print.get("date-parts") if isinstance(published_print, dict) else None
            ),
            "published_online": self.format_date_parts(
                published_online.get("date-parts") if isinstance(published_online, dict) else None
            ),
            "doc_type": self.map_doc_type(record.get("type", "")),
            "citation_count": record.get("is-referenced-by-count"),
            "reference_count": record.get("references-count"),
            "language": record.get("language"),
            "license_url": self.extract_license_url(record),
            "subjects": self.extract_subjects(record),
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
