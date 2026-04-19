"""Date extraction from PubMed XML elements.

Handles all date-related parsing including publication dates, history dates,
and article dates with support for partial dates and month name conversion.

MedlineDate Support (added 2026-01-25):
- Parses free-text MedlineDate elements like "2023 Jan-Feb", "2023 Spring"
- Extracts year (always first token)
- Maps seasons and quarters to month ranges (uses end-of-period)
- Handles month ranges by taking the second month (end-of-period strategy)

See: https://www.nlm.nih.gov/bsd/licensee/elements_descriptions.html
"""

from __future__ import annotations

__all__ = ["DateExtractor", "MedlineDateParser", "NormalizedDate", "RawDate"]


import calendar
import re
from typing import ClassVar, TypedDict, cast
from xml.etree.ElementTree import Element

from bioetl.application.pipelines.pubmed.extractors.base import BaseFieldExtractor
from bioetl.application.pipelines.pubmed.xml_parser import get_text


class RawDate(TypedDict):
    """Raw date components before normalization."""

    year: str | None
    month: str | None
    day: str | None


class NormalizedDate(TypedDict):
    """Normalized date result."""

    date_str: str | None
    year_int: int | None


class MedlineDateParser:
    """Parser for PubMed MedlineDate free-text format.

    Handles formats like:
    - "2023 Jan-Feb" → year=2023, month=Feb (end of range)
    - "2023 Spring" → year=2023, month=May (end of season)
    - "2023 1st Quart" → year=2023, month=Mar (end of Q1)
    - "2023 Jan" → year=2023, month=Jan
    - "2023" → year=2023
    - "2022 Dec-2023 Jan" → year=2023, month=Jan (cross-year: take second year)

    Uses end-of-period strategy: for ranges/seasons/quarters,
    returns the END of the period.
    """

    # Month abbreviation to number mapping
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

    # Season to end-of-period month mapping
    SEASON_MAP: ClassVar[dict[str, str]] = {
        "spring": "05",  # Mar-May → May (end)
        "spr": "05",
        "summer": "08",  # Jun-Aug → Aug (end)
        "sum": "08",
        "fall": "11",  # Sep-Nov → Nov (end)
        "autumn": "11",
        "aut": "11",
        "winter": "02",  # Dec-Feb → Feb (end of winter season)
        "win": "02",
    }

    # Quarter to end-of-period month mapping
    QUARTER_MAP: ClassVar[dict[str, str]] = {
        "1st": "03",  # Q1: Jan-Mar → Mar
        "2nd": "06",  # Q2: Apr-Jun → Jun
        "3rd": "09",  # Q3: Jul-Sep → Sep
        "4th": "12",  # Q4: Oct-Dec → Dec
        "q1": "03",
        "q2": "06",
        "q3": "09",
        "q4": "12",
    }

    # Pattern for month range: "Jan-Feb", "Dec-Jan" (NOT "Dec-2023")
    _MONTH_RANGE_PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r"\b([a-z]{3,9})-([a-z]{3,9})\b", re.IGNORECASE
    )

    # Pattern to find 4-digit years in text
    _YEAR_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"\b(19\d{2}|20\d{2})\b")

    def parse(self, medline_date: str) -> RawDate | None:
        """Parse MedlineDate free-text format into components.

        Args:
            medline_date: Free-text date string from MedlineDate element.

        Returns:
            RawDate with extracted year and month, or None if unparseable.
        """
        if not medline_date:
            return None

        text = medline_date.strip()
        tokens = text.split()

        if not tokens:
            return None

        # Pass original text instead of list of tokens to avoid unnecessary string join
        year = self._extract_year(text)
        if not year:
            return None

        month = self._extract_month(text, tokens)

        return RawDate(year=year, month=month, day=None)

    def _extract_year(self, text: str) -> str | None:
        """Extract year from MedlineDate text.

        Handles cross-year ranges like "2022 Dec-2023 Jan" by preferring
        the second (most recent) year if present.
        """
        # Optimized: perform regex search directly on the text string
        years_found: list[str] = self._YEAR_PATTERN.findall(text)

        if not years_found:
            return None

        # For cross-year ranges, take the last (most recent) year
        return years_found[-1]

    def _extract_month(self, text: str, tokens: list[str]) -> str | None:
        """Extract month/season/quarter from MedlineDate text.

        Uses end-of-period strategy for ranges.
        """
        # Check for month range pattern (e.g., "Jan-Feb")
        range_match = self._MONTH_RANGE_PATTERN.search(text)
        if range_match:
            return range_match.group(2)  # End-of-period: second month

        # Check for quarter (e.g., "1st Quart", "Q1")
        text_lower = text.lower()
        for quarter_key, month_num in self.QUARTER_MAP.items():
            if quarter_key in text_lower:
                return month_num

        # Check for season
        for token in tokens:
            token_lower = token.lower()
            if token_lower in self.SEASON_MAP:
                return self.SEASON_MAP[token_lower]

        # Check for single month name (pure alphabetic tokens only)
        # Process in reverse order to prefer later months (end-of-period)
        for token in reversed(tokens):
            if not token.isalpha():
                continue
            token_lower = token.lower()[:3]
            if token_lower in self.MONTH_MAP:
                return token

        return None


class DateExtractor(BaseFieldExtractor):
    """Extractor for date fields from PubMed XML.

    Handles:
    - Publication dates from JournalIssue/PubDate
    - History dates (received, accepted, revised)
    - Article dates (Electronic publication)
    - Partial dates (year only, year-month)
    - Month name to number conversion
    - MedlineDate free-text format (delegated to MedlineDateParser)
    """

    MONTH_MAP: ClassVar[dict[str, str]] = MedlineDateParser.MONTH_MAP
    _MEDLINE_PARSER: ClassVar[MedlineDateParser] = MedlineDateParser()
    _instance: ClassVar[DateExtractor | None] = None

    def __new__(cls) -> DateExtractor:
        """Implement Singleton pattern to reuse instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def extract(self, element: Element | None) -> RawDate | None:
        """Extract raw date components from an XML element.

        Supports both structured dates (Year/Month/Day elements) and
        free-text MedlineDate format ("2023 Jan-Feb", "2023 Spring", etc.).

        Args:
            element: XML element containing Year, Month, Day children
                or MedlineDate element.

        Returns:
            Dict with raw year, month, day strings, or None.
        """
        if element is None:
            return None

        year = get_text(element.find("Year"))
        month = get_text(element.find("Month"))
        day = get_text(element.find("Day"))

        # If structured components found, use them
        if any([year, month, day]):
            return RawDate(year=year, month=month, day=day)

        # Fallback: delegate to MedlineDate parser
        medline_date = get_text(element.find("MedlineDate"))
        if medline_date:
            return self._MEDLINE_PARSER.parse(medline_date)

        return None

    def normalize(self, raw_value: object) -> NormalizedDate:
        """Normalize date components into ISO format.

        Args:
            raw_value: Raw date components dict.

        Returns:
            Dict with formatted date_str and year_int.
        """
        raw_date = cast("RawDate", raw_value)
        year = raw_date.get("year")
        month = raw_date.get("month")
        day = raw_date.get("day")

        date_str = self._format_date(year, month, day)
        year_int = int(year) if year and year.isdigit() else None

        return NormalizedDate(date_str=date_str, year_int=year_int)

    def _format_date(
        self,
        year: str | None,
        month: str | None,
        day: str | None,
    ) -> str | None:
        """Format date components into ISO date string (YYYY-MM-DD).

        Uses end-of-period strategy for partial dates:
        - Year + Month + Day → YYYY-MM-DD
        - Year + Month (no day) → YYYY-MM-last_day
        - Year only → YYYY-12-31
        """
        if not year:
            return None

        # Normalize month
        if month:
            month_str = month.strip().lower()[:3]
            month_num = self.MONTH_MAP.get(month_str)
            if not month_num and month.isdigit():
                month_num = month.zfill(2)
            if not month_num:
                # Unknown month format → treat as year-only
                return f"{year}-12-31"
        else:
            # No month → year-only
            return f"{year}-12-31"

        # Normalize day (end of month if missing)
        if day and day.isdigit():
            day_num = day.zfill(2)
        else:
            # Calculate last day of month
            try:
                _, last_day = calendar.monthrange(int(year), int(month_num))
                day_num = str(last_day).zfill(2)
            except (ValueError, IndexError):
                # Fallback to 30 if invalid year/month or calculation fails
                day_num = "30"

        return f"{year}-{month_num}-{day_num}"

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
