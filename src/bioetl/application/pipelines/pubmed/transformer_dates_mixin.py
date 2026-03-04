"""Date and journal extraction helpers for PubMed transformer."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import TYPE_CHECKING

from bioetl.application.pipelines.pubmed.extractors import DateExtractor
from bioetl.application.pipelines.pubmed.xml_parser import get_text
from bioetl.domain.normalization import parse_page_range
from bioetl.domain.value_objects import PublicationYear

if TYPE_CHECKING:
    from collections.abc import Callable

    from bioetl.domain.ports import DataNormalizationPort


class _PubMedTransformerDatesMixin:
    """Provides PubMed date/journal extraction routines."""

    _VALID_DATE_PATTERNS: tuple[re.Pattern[str], ...]
    _MONTH_MAP: dict[str, int]
    _data_normalizer: DataNormalizationPort
    _date_extractor: DateExtractor
    validate_value_object: Callable[..., str | int | None]

    def _is_valid_date_format(self, date_str: str | None) -> bool:
        """Validate that date string matches YYYY, YYYY-MM, or YYYY-MM-DD format."""
        if not date_str:
            return False
        return any(pattern.match(date_str) for pattern in self._VALID_DATE_PATTERNS)

    def _extract_journal_data(
        self,
        article: ET.Element,
    ) -> dict[str, object]:
        """Extract journal-related data from article XML."""
        journal_elem = article.find(".//Journal")
        pages = get_text(article.find(".//Pagination/MedlinePgn"))
        first_page, last_page = parse_page_range(pages)

        if not journal_elem:
            return {
                "journal": None,
                "journal_name_short": None,
                "journal_iso_abbrev": None,
                "journal_issn_type": None,
                "issn": None,
                "volume": None,
                "issue": None,
                "page_range": pages,
                "medline_pgn": pages,
                "page_first": first_page,
                "page_last": last_page,
            }

        journal_issue = journal_elem.find("JournalIssue")
        journal_title = get_text(journal_elem.find("Title"))
        journal_abbrev = get_text(journal_elem.find("ISOAbbreviation"))
        issn_elem = journal_elem.find("ISSN")
        issn = get_text(issn_elem)
        issn_type = issn_elem.get("IssnType") if issn_elem is not None else None

        return {
            "journal": journal_title,
            "journal_name_short": journal_abbrev,
            "journal_iso_abbrev": journal_abbrev,
            "journal_issn_type": issn_type,
            "issn": issn,
            "volume": get_text(journal_issue.find("Volume")) if journal_issue else None,
            "issue": get_text(journal_issue.find("Issue")) if journal_issue else None,
            "page_range": pages,
            "medline_pgn": pages,
            "page_first": first_page,
            "page_last": last_page,
        }

    def _compute_publication_date(
        self,
        epub_date: str | None,
        pub_date: str | None,
        year: int | None,
    ) -> str | None:
        """Compute unified publication_date (YYYY-MM-DD)."""
        if epub_date and len(epub_date) >= 10:
            return epub_date[:10]

        if pub_date:
            return self._data_normalizer.normalize_partial_date(pub_date)

        if year:
            return f"{year}-12-31"

        return None

    def _parse_month_day(
        self,
        pub_date_node: ET.Element | None,
    ) -> tuple[int | None, int | None]:
        """Extract month and day as integers from PubDate node."""
        if pub_date_node is None:
            return None, None

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

    def _extract_date_data(
        self,
        article: ET.Element,
        pubmed_data: ET.Element | None,
        medline: ET.Element | None,
    ) -> dict[str, object]:
        """Extract normalized date fields from article and MedlineCitation XML."""
        journal = article.find(".//Journal")
        journal_issue = journal.find("JournalIssue") if journal else None
        pub_date_node = journal_issue.find("PubDate") if journal_issue else None
        raw_pub_date, raw_year = DateExtractor.extract_date(pub_date_node)

        pub_month, pub_day = self._parse_month_day(pub_date_node)

        _validated_year = self.validate_value_object(
            PublicationYear, raw_year, as_string=False
        )
        validated_year: int | None = (
            int(_validated_year) if _validated_year is not None else None
        )

        raw_epub_date = DateExtractor.extract_article_date(article, "Electronic")

        pub_date = raw_pub_date if self._is_valid_date_format(raw_pub_date) else None
        epub_date = raw_epub_date if self._is_valid_date_format(raw_epub_date) else None

        publication_date = self._compute_publication_date(
            epub_date, pub_date, validated_year
        )

        date_completed, _ = (
            DateExtractor.extract_date(medline.find("DateCompleted"))
            if medline is not None
            else (None, None)
        )
        date_revised, _ = (
            DateExtractor.extract_date(medline.find("DateRevised"))
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
