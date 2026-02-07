"""Date extraction helper for PubMed.

This module contains helper logic extracted from PubMedPublicationTransformer
to reduce class complexity and line count.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Any, ClassVar

from bioetl.application.pipelines.pubmed.extractors.date import DateExtractor
from bioetl.domain.value_objects import PublicationYear


class PubMedDateHelper:
    """Helper for extracting and normalizing date information from PubMed XML.

    Encapsulates date validation, extraction, and normalization logic.
    """

    # Date validation patterns for ISO date formats (YYYY, YYYY-MM, YYYY-MM-DD).
    # Used to filter out invalid dates like "2024-13-99" or "n/a" before
    # they propagate to _compute_publication_date.
    _VALID_DATE_PATTERNS: tuple[re.Pattern[str], ...] = (
        # Full date: YYYY-MM-DD (with valid month 01-12 and day 01-31)
        re.compile(r"^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$"),
        # Partial month: YYYY-MM (with valid month 01-12)
        re.compile(r"^\d{4}-(0[1-9]|1[0-2])$"),
        # Partial year: YYYY
        re.compile(r"^\d{4}$"),
    )

    _MONTH_MAP: ClassVar[dict[str, int]] = {
        "jan": 1,
        "feb": 2,
        "mar": 3,
        "apr": 4,
        "may": 5,
        "jun": 6,
        "jul": 7,
        "aug": 8,
        "sep": 9,
        "oct": 10,
        "nov": 11,
        "dec": 12,
    }

    def __init__(self) -> None:
        """Initialize helper with reused DateExtractor instance."""
        self._date_extractor = DateExtractor()

    def is_valid_date_format(self, date_str: str | None) -> bool:
        """Validate that date string matches expected ISO format.

        Accepts:
        - YYYY-MM-DD (full date with valid month 01-12 and day 01-31)
        - YYYY-MM (partial with valid month 01-12)
        - YYYY (year only)

        Args:
            date_str: Date string to validate.

        Returns:
            True if date format is valid, False otherwise.
        """
        if not date_str:
            return False
        return any(pattern.match(date_str) for pattern in self._VALID_DATE_PATTERNS)

    def extract_date_data(
        self,
        article: ET.Element,
        pubmed_data: ET.Element | None,
        medline: ET.Element | None,
    ) -> dict[str, Any]:
        """Extract date-related data from article and MedlineCitation XML.

        Validates date formats before use to prevent invalid dates.

        Args:
            article: Article XML element.
            pubmed_data: PubmedData XML element.
            medline: MedlineCitation XML element.

        Returns:
            Dictionary with all date-related fields.
        """
        journal = article.find(".//Journal")
        journal_issue = journal.find("JournalIssue") if journal else None
        pub_date_node = journal_issue.find("PubDate") if journal_issue else None
        raw_pub_date, raw_year = self._extract_date_helper(pub_date_node)

        pub_month, pub_day = self._parse_month_day(pub_date_node)

        year_vo = PublicationYear.from_raw(raw_year)
        validated_year = year_vo.value if year_vo else None

        raw_epub_date = self._extract_article_date_helper(article, "Electronic")

        # Validate date formats before passing to _compute_publication_date.
        pub_date = raw_pub_date if self.is_valid_date_format(raw_pub_date) else None
        epub_date = raw_epub_date if self.is_valid_date_format(raw_epub_date) else None

        publication_date = self._compute_publication_date(
            epub_date, pub_date, validated_year
        )

        # Extract MEDLINE indexing dates from MedlineCitation element
        date_completed, _ = (
            self._extract_date_helper(medline.find("DateCompleted"))
            if medline is not None
            else (None, None)
        )
        date_revised, _ = (
            self._extract_date_helper(medline.find("DateRevised"))
            if medline is not None
            else (None, None)
        )

        return {
            "pub_date": pub_date,
            "pub_month": pub_month,
            "pub_day": pub_day,
            "publication_date": publication_date,
            "publication_year": validated_year,
            "date_completed": date_completed,
            "date_revised": date_revised,
        }

    def _extract_date_helper(
        self, date_node: ET.Element | None
    ) -> tuple[str | None, int | None]:
        """Extract date using reused DateExtractor instance."""
        raw = self._date_extractor.extract(date_node)
        if raw is None:
            return None, None
        normalized = self._date_extractor.normalize(raw)
        return normalized["date_str"], normalized["year_int"]

    def _extract_article_date_helper(
        self, article_node: ET.Element | None, date_type: str
    ) -> str | None:
        """Extract article date using reused DateExtractor instance."""
        if article_node is None:
            return None

        for date_node in article_node.findall(".//ArticleDate"):
            if date_node.get("DateType") == date_type:
                date_str, _ = self._extract_date_helper(date_node)
                return date_str
        return None

    def _parse_month_day(
        self, pub_date_node: ET.Element | None
    ) -> tuple[int | None, int | None]:
        """Extract month and day as integers from PubDate node."""
        if pub_date_node is None:
            return None, None

        # Use DateExtractor logic to support MedlineDate parsing
        raw_date = self._date_extractor.extract(pub_date_node)
        if not raw_date:
            return None, None

        month_text = raw_date.get("month")
        day_text = raw_date.get("day")

        pub_month = self._parse_month(month_text)
        pub_day = int(day_text) if day_text and day_text.isdigit() else None

        return pub_month, pub_day

    def _parse_month(self, month_text: str | None) -> int | None:
        """Convert month text (name or number) to integer."""
        if not month_text:
            return None

        month_lower = month_text.strip().lower()[:3]
        result = self._MONTH_MAP.get(month_lower)
        if result is None and month_text.isdigit():
            result = int(month_text)
        return result

    def _compute_publication_date(
        self, epub_date: str | None, pub_date: str | None, year: int | None
    ) -> str | None:
        """Compute unified publication_date (YYYY-MM-DD).

        Priority: epub_date > pub_date > year
        All outputs normalized to full YYYY-MM-DD format using end-of-period strategy.
        """
        # Priority 1: epub_date if it's a complete date
        if epub_date and len(epub_date) >= 10:
            return epub_date[:10]

        # Priority 2: pub_date (may be partial, normalize it)
        if pub_date:
            return self._normalize_partial_date(pub_date)

        # Priority 3: Construct from year (end of year)
        if year:
            return f"{year}-12-31"

        return None

    def _normalize_partial_date(self, date_str: str) -> str:
        """Normalize partial date string to YYYY-MM-DD (end of period).

        Assumes date_str is already validated by is_valid_date_format.
        """
        if len(date_str) == 10:  # YYYY-MM-DD
            return date_str
        if len(date_str) == 7:  # YYYY-MM
            import calendar

            year = int(date_str[:4])
            month = int(date_str[5:7])
            _, last_day = calendar.monthrange(year, month)
            return f"{date_str}-{last_day:02d}"
        if len(date_str) == 4:  # YYYY
            return f"{date_str}-12-31"
        return date_str
