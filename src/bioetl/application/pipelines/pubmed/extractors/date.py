"""Date extraction from PubMed XML elements.

Handles all date-related parsing including publication dates, history dates,
and article dates with support for partial dates and month name conversion.
"""

from __future__ import annotations

from typing import ClassVar, TypedDict
from xml.etree.ElementTree import Element

from bioetl.application.pipelines.pubmed.extractors.base import BaseFieldExtractor
from bioetl.application.pipelines.pubmed.xml_utils import get_text


class RawDate(TypedDict):
    """Raw date components before normalization."""

    year: str | None
    month: str | None
    day: str | None


class NormalizedDate(TypedDict):
    """Normalized date result."""

    date_str: str | None
    year_int: int | None


class DateExtractor(BaseFieldExtractor):
    """Extractor for date fields from PubMed XML.

    Handles:
    - Publication dates from JournalIssue/PubDate
    - History dates (received, accepted, revised)
    - Article dates (Electronic publication)
    - Partial dates (year only, year-month)
    - Month name to number conversion
    """

    MONTH_MAP: ClassVar[dict[str, str]] = {
        "jan": "01",
        "feb": "02",
        "mar": "03",
        "apr": "04",
        "may": "05",
        "jun": "06",
        "jul": "07",
        "aug": "08",
        "sep": "09",
        "oct": "10",
        "nov": "11",
        "dec": "12",
    }

    def extract(self, element: Element | None) -> RawDate | None:
        """Извлечь сырые компоненты даты из XML элемента.

        Args:
            element: XML element containing Year, Month, Day children.

        Returns:
            Dict with raw year, month, day strings, or None.
        """
        if element is None:
            return None

        year = get_text(element.find("Year"))
        month = get_text(element.find("Month"))
        day = get_text(element.find("Day"))

        # Return None if no date components found
        if not any([year, month, day]):
            return None

        return RawDate(year=year, month=month, day=day)

    def normalize(self, raw_value: RawDate) -> NormalizedDate:
        """Нормализовать компоненты даты в ISO формат.

        Args:
            raw_value: Raw date components dict.

        Returns:
            Dict with formatted date_str and year_int.
        """
        year = raw_value.get("year")
        month = raw_value.get("month")
        day = raw_value.get("day")

        date_str = self._format_date(year, month, day)
        year_int = int(year) if year and year.isdigit() else None

        return NormalizedDate(date_str=date_str, year_int=year_int)

    def _format_date(
        self,
        year: str | None,
        month: str | None,
        day: str | None,
    ) -> str | None:
        """Format date components into ISO date string (YYYY-MM-DD or partial)."""
        if not year:
            return None

        parts = [year]
        if month:
            month_lower = month.lower()[:3]
            month_num = self.MONTH_MAP.get(month_lower, month.zfill(2))
            parts.append(month_num)

            if day:
                parts.append(day.zfill(2))

        return "-".join(parts)

    @classmethod
    def format_date(
        cls,
        year: str | None,
        month: str | None,
        day: str | None,
    ) -> str | None:
        """Format date components into ISO date string (YYYY-MM-DD or partial).

        Args:
            year: Year as string (required for non-None result).
            month: Month as string (numeric or name).
            day: Day as string.

        Returns:
            ISO formatted date string or None if year is missing.
        """
        return cls()._format_date(year, month, day)

    @classmethod
    def extract_date(
        cls,
        date_node: Element | None,
    ) -> tuple[str | None, int | None]:
        """Extract date string and year from a date element.

        Args:
            date_node: XML element containing Year, Month, Day children.

        Returns:
            Tuple of (formatted_date_string, year_int).
        """
        extractor = cls()
        raw = extractor.extract(date_node)
        if raw is None:
            return None, None
        normalized = extractor.normalize(raw)
        return normalized["date_str"], normalized["year_int"]

    @classmethod
    def extract_history_date(
        cls,
        history_node: Element | None,
        pub_status: str,
    ) -> str | None:
        """Extract a specific date from PubMedPubDate history.

        Args:
            history_node: The History element from PubmedData.
            pub_status: PubStatus value to look for (received, revised, accepted).

        Returns:
            ISO formatted date string or None.
        """
        if history_node is None:
            return None

        for date_node in history_node.findall("PubMedPubDate"):
            if date_node.get("PubStatus") == pub_status:
                date_str, _ = cls.extract_date(date_node)
                return date_str
        return None

    @classmethod
    def extract_article_date(
        cls,
        article_node: Element | None,
        date_type: str,
    ) -> str | None:
        """Extract date from ArticleDate element by DateType attribute.

        Args:
            article_node: The Article element.
            date_type: DateType attribute value (e.g., "Electronic").

        Returns:
            ISO formatted date string or None.
        """
        if article_node is None:
            return None

        for date_node in article_node.findall(".//ArticleDate"):
            if date_node.get("DateType") == date_type:
                date_str, _ = cls.extract_date(date_node)
                return date_str
        return None
