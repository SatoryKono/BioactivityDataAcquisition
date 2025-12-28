"""CrossRef Publication Transformer.

Transforms CrossRef API responses to Silver format.
See: https://api.crossref.org/swagger-ui/index.html
"""

from __future__ import annotations

import html
import re
from typing import TYPE_CHECKING, Any, cast

from bioetl.application.core.base_transformer import BaseTransformer
from bioetl.domain.entities import CrossRefPublication
from bioetl.domain.transformations import generate_entity_id

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.filtering import GoldFilterConfig
    from bioetl.domain.ports import MetricsPort, TracingPort
    from bioetl.domain.types import BronzeRecord, SilverRecord


class CrossRefPublicationTransformer(BaseTransformer):
    """Transformer for CrossRef publication records."""

    def __init__(
        self,
        provider: str = "crossref",
        entity_type: str = "publication",
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
        gold_filters: GoldFilterConfig | None = None,
    ):
        """Initialize CrossRef publication transformer.

        Args:
            provider: Data provider identifier.
            entity_type: Entity type for metrics labels.
            tracer: Optional tracing port for distributed tracing (O1 observability).
            metrics: Optional metrics port for duration/error tracking (O1 observability).
            gold_filters: Optional filter configuration for Gold layer.

        """
        super().__init__(
            provider,
            entity_type=entity_type,
            tracer=tracer,
            metrics=metrics,
            gold_filters=gold_filters,
        )

    async def _transform_impl(
        self, context: PipelineContext, record: BronzeRecord, index: int
    ) -> SilverRecord | None:
        """Transform raw CrossRef API record to Silver format.

        Args:
            context: Pipeline context with run_id, run_type, logger.
            record: Raw Bronze record from CrossRef API.
            index: Sequential index of the record in the pipeline run.

        Returns:
            SilverRecord if transformation successful, None if record should be skipped.

        """
        # Get DOI as primary key
        raw_doi = record.get("DOI")
        if not raw_doi or not isinstance(raw_doi, str):
            context.logger.warning(
                "crossref_missing_doi",
                provider=self.provider,
            )
            return None

        # Normalize DOI
        doi = self._normalize_doi(raw_doi)

        # Extract business data
        business_data = self._extract_business_data(record, doi)

        # Generate entity ID
        entity_id = generate_entity_id(
            record={"doi": doi}, provider=self.provider, id_field="doi"
        )

        # Compute content hash
        content_hash = self.compute_content_hash(business_data, exclude_none=False)

        # Create entity
        entity = self._create_entity(
            CrossRefPublication,
            context,
            entity_id=entity_id,
            content_hash=content_hash,
            index=index,
            **business_data,
        )

        return cast("SilverRecord", self.entity_to_silver_record(entity))

    def _extract_business_data(
        self, record: BronzeRecord, doi: str
    ) -> dict[str, Any]:
        """Extract all business fields from CrossRef API response.

        Args:
            record: Raw CrossRef API record.
            doi: Normalized DOI.

        Returns:
            Dictionary of business fields for entity creation.

        """
        # Extract basic metadata
        title = self._extract_title(record)
        abstract = self._extract_abstract(record)
        authors = self._extract_authors(record)

        # Extract journal info
        journal = self._extract_first_item(record.get("container-title"))
        issn = self._extract_first_item(record.get("ISSN"))
        volume = record.get("volume")
        issue = record.get("issue")

        # Extract page info
        page_value = record.get("page")
        page_str = str(page_value) if page_value is not None else None
        first_page, last_page = self._extract_pages(page_str)

        # Extract dates
        year, published_date = self._extract_publication_date(record)

        # Extract document type
        doc_type = record.get("type")

        # Extract metrics
        citation_count = record.get("is-referenced-by-count")
        references_count = record.get("references-count")

        # Extract publisher
        publisher = record.get("publisher")

        # Extract additional identifiers
        pmid = self._extract_pmid(record)
        pmc_id = self._extract_pmc_id(record)

        # Extract subjects
        subjects = record.get("subject", [])
        if not isinstance(subjects, list):
            subjects = []

        # Extract funders (serialize as JSON)
        funders = self.serialize_json(record.get("funder"))

        # Extract license
        license_url = self._extract_license(record)

        # Extract URL
        url = record.get("URL")

        return {
            "doi": doi,
            "title": title,
            "abstract": abstract,
            "authors": authors,
            "journal": journal,
            "issn": issn,
            "volume": volume,
            "issue": issue,
            "first_page": first_page,
            "last_page": last_page,
            "year": year,
            "published_date": published_date,
            "doc_type": doc_type,
            "citation_count": citation_count,
            "references_count": references_count,
            "publisher": publisher,
            "pmid": pmid,
            "pmc_id": pmc_id,
            "subjects": subjects,
            "funders": funders,
            "license_url": license_url,
            "url": url,
        }

    @staticmethod
    def _normalize_doi(doi: str) -> str:
        """Normalize DOI to lowercase and strip whitespace.

        Args:
            doi: Raw DOI string.

        Returns:
            Normalized DOI.

        """
        return doi.strip().lower()

    @staticmethod
    def _extract_title(record: BronzeRecord) -> str | None:
        """Extract title from record.

        CrossRef returns title as a list, we take the first element.

        Args:
            record: CrossRef API record.

        Returns:
            Title string or None.

        """
        title_list = record.get("title")
        if isinstance(title_list, list) and title_list:
            title = title_list[0]
            # Clean up HTML entities
            if isinstance(title, str):
                return html.unescape(title).strip()
            return str(title)
        return None

    @staticmethod
    def _extract_abstract(record: BronzeRecord) -> str | None:
        """Extract and clean abstract from record.

        CrossRef abstracts may contain HTML tags (typically <jats:p> etc.)

        Args:
            record: CrossRef API record.

        Returns:
            Cleaned abstract string or None.

        """
        abstract = record.get("abstract")
        if not abstract or not isinstance(abstract, str):
            return None

        # Remove HTML/XML tags
        clean = re.sub(r"<[^>]+>", "", abstract)
        # Unescape HTML entities
        clean = html.unescape(clean)
        # Clean up whitespace
        clean = " ".join(clean.split())

        return clean.strip() if clean else None

    @staticmethod
    def _extract_authors(record: BronzeRecord) -> list[str]:
        """Extract author names from record.

        CrossRef returns authors as list of objects with given/family fields.

        Args:
            record: CrossRef API record.

        Returns:
            List of author name strings.

        """
        authors: list[str] = []
        author_list = record.get("author", [])

        if not isinstance(author_list, list):
            return authors

        for author in author_list:
            if not isinstance(author, dict):
                continue

            given = author.get("given", "").strip()
            family = author.get("family", "").strip()

            if given and family:
                authors.append(f"{given} {family}")
            elif family:
                authors.append(family)
            elif given:
                authors.append(given)
            # Handle corporate authors
            elif author.get("name"):
                authors.append(author.get("name", "").strip())

        return authors

    @staticmethod
    def _extract_first_item(value: Any) -> str | None:
        """Extract first item from a list or return as-is if string.

        Args:
            value: List or string value.

        Returns:
            First item as string or None.

        """
        if isinstance(value, list) and value:
            item = value[0]
            return str(item) if item is not None else None
        if isinstance(value, str):
            return value
        return None

    @staticmethod
    def _extract_pages(page: str | None) -> tuple[str | None, str | None]:
        """Extract first and last page from page string.

        CrossRef uses format "123-456" or just "123".

        Args:
            page: Page string from CrossRef.

        Returns:
            Tuple of (first_page, last_page).

        """
        if not page or not isinstance(page, str):
            return None, None

        page = page.strip()
        if "-" in page:
            parts = page.split("-", 1)
            return parts[0].strip() or None, parts[1].strip() or None

        return page, None

    @staticmethod
    def _extract_publication_date(
        record: BronzeRecord,
    ) -> tuple[int | None, str | None]:
        """Extract publication year and date from record.

        CrossRef uses date-parts format: [[year, month, day]] or [[year, month]].
        Priority: published-print > published-online > created

        Args:
            record: CrossRef API record.

        Returns:
            Tuple of (year as int, full date as ISO string or None).

        """
        # Try different date fields in priority order
        date_fields = [
            "published-print",
            "published-online",
            "published",
            "created",
        ]

        for field in date_fields:
            date_obj = record.get(field)
            if not isinstance(date_obj, dict):
                continue

            date_parts = date_obj.get("date-parts")
            if not date_parts or not isinstance(date_parts, list):
                continue

            # date-parts is [[year, month, day]] format
            parts = date_parts[0] if date_parts else []
            if not parts or not isinstance(parts, list):
                continue

            year = parts[0] if len(parts) > 0 else None
            month = parts[1] if len(parts) > 1 else None
            day = parts[2] if len(parts) > 2 else None

            # Validate year
            if year is None or not isinstance(year, int):
                continue

            # Build date string
            date_str = None
            if year and month and day:
                date_str = f"{year:04d}-{month:02d}-{day:02d}"
            elif year and month:
                date_str = f"{year:04d}-{month:02d}"

            return year, date_str

        return None, None

    @staticmethod
    def _extract_pmid(record: BronzeRecord) -> str | None:
        """Extract PubMed ID from alternative-id or link fields.

        Args:
            record: CrossRef API record.

        Returns:
            PMID string or None.

        """
        # Check alternative-id
        alt_ids = record.get("alternative-id", [])
        if isinstance(alt_ids, list):
            for alt_id in alt_ids:
                if isinstance(alt_id, str) and alt_id.isdigit():
                    # Could be PMID
                    return alt_id

        # Check links for PubMed
        links = record.get("link", [])
        if isinstance(links, list):
            for link in links:
                if isinstance(link, dict):
                    url = link.get("URL", "")
                    if "pubmed" in url.lower():
                        # Extract PMID from URL
                        match = re.search(r"/(\d+)", url)
                        if match:
                            return match.group(1)

        return None

    @staticmethod
    def _extract_pmc_id(record: BronzeRecord) -> str | None:
        """Extract PubMed Central ID from record.

        Args:
            record: CrossRef API record.

        Returns:
            PMC ID string or None.

        """
        # Check links for PMC
        links = record.get("link", [])
        if isinstance(links, list):
            for link in links:
                if isinstance(link, dict):
                    url = link.get("URL", "")
                    if "pmc" in url.lower():
                        match = re.search(r"PMC\d+", url, re.IGNORECASE)
                        if match:
                            return match.group(0).upper()

        return None

    @staticmethod
    def _extract_license(record: BronzeRecord) -> str | None:
        """Extract license URL from record.

        Args:
            record: CrossRef API record.

        Returns:
            License URL string or None.

        """
        licenses = record.get("license", [])
        if isinstance(licenses, list) and licenses:
            first_license = licenses[0]
            if isinstance(first_license, dict):
                return first_license.get("URL")
        return None
