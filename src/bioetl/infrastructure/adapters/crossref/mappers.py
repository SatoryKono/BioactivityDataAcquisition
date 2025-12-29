"""CrossRef API response to domain entity mappers.

Transforms CrossRef API responses to domain entities (Work).
Implements field extraction and normalization per task specification.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from bioetl.domain.entities.crossref import CROSSREF_TYPE_MAP, Work
from bioetl.domain.types import ContentHash, EntityID, RunID, RunType

# HTML tag pattern for stripping from abstract
HTML_TAG_PATTERN = re.compile(r"<[^>]+>")


class WorkToPublicationMapper:
    """Maps CrossRef API work response to Work domain entity.

    Handles field extraction, normalization, and type coercion
    according to the CrossRef → Publication mapping specification.
    """

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
        return HTML_TAG_PATTERN.sub("", text).strip()

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
        return WorkToPublicationMapper.strip_html_tags(abstract) or None

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

    def map_to_work(
        self,
        work_data: dict[str, Any],
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
        content_hash: ContentHash,
        index: int,
    ) -> Work:
        """Map CrossRef API work response to Work domain entity.

        Args:
            work_data: Raw CrossRef work record.
            run_id: Pipeline run correlation ID.
            run_type: Type of pipeline run.
            ingestion_ts: Ingestion timestamp.
            content_hash: Pre-computed content hash.
            index: Record index in the pipeline run.

        Returns:
            Work domain entity.

        """
        doi = self.normalize_doi(work_data.get("DOI", ""))
        first_page, last_page = self.extract_pages(work_data)

        # Extract date fields
        published_print = work_data.get("published-print", {})
        published_online = work_data.get("published-online", {})

        return Work(
            # Base entity fields
            entity_id=EntityID(doi),
            content_hash=content_hash,
            run_id=run_id,
            run_type=run_type,
            ingestion_ts=ingestion_ts,
            _index=index,
            # CrossRef-specific fields
            doi=doi,
            title=self.extract_title(work_data),
            abstract=self.extract_abstract(work_data),
            authors=self.extract_authors(work_data),
            journal=self.extract_journal(work_data),
            issn=self.extract_issn(work_data),
            publisher=work_data.get("publisher"),
            volume=work_data.get("volume"),
            issue=work_data.get("issue"),
            first_page=first_page,
            last_page=last_page,
            year=self.extract_year(work_data),
            published_print=self.format_date_parts(
                published_print.get("date-parts")
            ),
            published_online=self.format_date_parts(
                published_online.get("date-parts")
            ),
            doc_type=self.map_doc_type(work_data.get("type", "")),
            citation_count=work_data.get("is-referenced-by-count"),
            reference_count=work_data.get("references-count"),
            language=work_data.get("language"),
            license_url=self.extract_license_url(work_data),
            subjects=self.extract_subjects(work_data),
            source="crossref",
        )

    def map_to_dict(self, work_data: dict[str, Any]) -> dict[str, Any]:
        """Map CrossRef API work response to dictionary for Bronze storage.

        Performs field extraction and normalization without creating entity.
        Used for Bronze layer storage before entity conversion.

        Args:
            work_data: Raw CrossRef work record.

        Returns:
            Normalized dictionary for Bronze storage.

        """
        doi = self.normalize_doi(work_data.get("DOI", ""))
        first_page, last_page = self.extract_pages(work_data)

        # Extract date fields
        published_print = work_data.get("published-print", {})
        published_online = work_data.get("published-online", {})

        return {
            "doi": doi,
            "title": self.extract_title(work_data),
            "abstract": self.extract_abstract(work_data),
            "authors": self.extract_authors(work_data),
            "journal": self.extract_journal(work_data),
            "issn": self.extract_issn(work_data),
            "publisher": work_data.get("publisher"),
            "volume": work_data.get("volume"),
            "issue": work_data.get("issue"),
            "first_page": first_page,
            "last_page": last_page,
            "year": self.extract_year(work_data),
            "published_print": self.format_date_parts(
                published_print.get("date-parts")
            ),
            "published_online": self.format_date_parts(
                published_online.get("date-parts")
            ),
            "doc_type": self.map_doc_type(work_data.get("type", "")),
            "citation_count": work_data.get("is-referenced-by-count"),
            "reference_count": work_data.get("references-count"),
            "language": work_data.get("language"),
            "license_url": self.extract_license_url(work_data),
            "subjects": self.extract_subjects(work_data),
            "source": "crossref",
            # Preserve raw type for debugging
            "_raw_type": work_data.get("type"),
        }
