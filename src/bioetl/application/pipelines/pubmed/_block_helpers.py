"""Shared private helpers for PubMed extraction blocks and transformer seams."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING

from bioetl.application.pipelines.pubmed.extractors.author import (
    RawAuthor,
    StructuredAffiliation,
)
from bioetl.application.pipelines.pubmed.extractors.date import DateExtractor
from bioetl.application.pipelines.pubmed.xml_parser import get_text
from bioetl.domain.normalization import parse_page_range
from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from bioetl.domain.ports import DataNormalizationPort, PiiHasherPort


def process_structured_affiliations(
    affiliations: Sequence[StructuredAffiliation],
    pii_hasher: PiiHasherPort | None,
) -> list[JsonDict]:
    """Process structured affiliations with PII-safe email hashing."""
    processed: list[JsonDict] = []
    for affiliation in affiliations:
        processed_affiliation: JsonDict = {
            "text": affiliation.get("text"),
            "identifier": affiliation.get("identifier"),
            "identifier_source": affiliation.get("identifier_source"),
            "ror_id": affiliation.get("ror_id"),
            "grid_id": affiliation.get("grid_id"),
        }
        email = affiliation.get("email")
        processed_affiliation["email_hash"] = (
            pii_hasher.hash_value(email) if email and pii_hasher else None
        )
        processed.append(processed_affiliation)
    return processed


def build_authors_with_affiliations(
    raw_authors: Sequence[RawAuthor],
    pii_hasher: PiiHasherPort | None,
) -> list[JsonDict]:
    """Build structured author-affiliation mapping with hashed author names."""
    authors_with_affiliations: list[JsonDict] = []
    for author in raw_authors:
        author_name = _resolve_author_name(author)
        if author_name is None:
            continue

        affiliations: list[JsonDict] = []
        for affiliation in author.get("structured_affiliations") or []:
            affiliations.append(
                {
                    "text": affiliation.get("text"),
                    "ror_id": affiliation.get("ror_id"),
                    "grid_id": affiliation.get("grid_id"),
                    "identifier": affiliation.get("identifier"),
                    "identifier_source": affiliation.get("identifier_source"),
                }
            )

        authors_with_affiliations.append(
            {
                "name_hash": pii_hasher.hash_value(author_name) if pii_hasher else None,
                "initials": author.get("initials"),
                "affiliations": affiliations,
            }
        )
    return authors_with_affiliations


def _resolve_author_name(author: RawAuthor) -> str | None:
    last_name = author.get("last_name")
    initials = author.get("initials")
    fore_name = author.get("fore_name")
    collective = author.get("collective_name")

    if last_name:
        if initials:
            return f"{last_name}, {initials}"
        if fore_name:
            return f"{last_name}, {fore_name}"
        return last_name
    return collective


def extract_journal_data(article: ET.Element) -> dict[str, object]:
    """Extract journal metadata from PubMed article XML."""
    journal_element = article.find(".//Journal")
    pages = get_text(article.find(".//Pagination/MedlinePgn"))
    first_page, last_page = parse_page_range(pages)

    if journal_element is None:
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

    journal_issue = journal_element.find("JournalIssue")
    issn_element = journal_element.find("ISSN")
    journal_abbrev = get_text(journal_element.find("ISOAbbreviation"))
    return {
        "journal": get_text(journal_element.find("Title")),
        "journal_name_short": journal_abbrev,
        "journal_iso_abbrev": journal_abbrev,
        "journal_issn_type": issn_element.get("IssnType")
        if issn_element is not None
        else None,
        "issn": get_text(issn_element),
        "volume": get_text(journal_issue.find("Volume")) if journal_issue else None,
        "issue": get_text(journal_issue.find("Issue")) if journal_issue else None,
        "page_range": pages,
        "medline_pgn": pages,
        "page_first": first_page,
        "page_last": last_page,
    }


def is_valid_date_format(
    date_value: str | None,
    valid_date_patterns: Sequence[re.Pattern[str]],
) -> bool:
    """Validate that date string matches allowed ISO-like formats."""
    if not date_value:
        return False
    return any(pattern.match(date_value) for pattern in valid_date_patterns)


def compute_publication_date(
    *,
    data_normalizer: DataNormalizationPort,
    epub_date: str | None,
    pub_date: str | None,
    year: int | None,
) -> str | None:
    """Resolve final publication date with epub > pub_date > year priority."""
    if epub_date and len(epub_date) >= 10:
        return epub_date[:10]
    if pub_date:
        return data_normalizer.normalize_partial_date(pub_date)
    if year:
        return f"{year}-12-31"
    return None


def parse_month(
    month_text: str | None,
    month_map: dict[str, int],
) -> int | None:
    """Convert month name or number to integer."""
    if not month_text:
        return None

    month_key = month_text.strip().lower()[:3]
    resolved = month_map.get(month_key)
    if resolved is None and month_text.isdigit():
        return int(month_text)
    return resolved


def parse_month_day(
    pub_date_node: ET.Element | None,
    *,
    date_extractor: DateExtractor,
    month_map: dict[str, int],
) -> tuple[int | None, int | None]:
    """Extract month and day as integers from PubDate node."""
    if pub_date_node is None:
        return None, None

    raw_date = date_extractor.extract(pub_date_node)
    if not raw_date:
        return None, None

    day_text = raw_date.get("day")
    return (
        parse_month(raw_date.get("month"), month_map),
        int(day_text) if day_text and day_text.isdigit() else None,
    )


def extract_date_data(
    *,
    article: ET.Element,
    pubmed_data: ET.Element | None,
    medline: ET.Element | None,
    date_extractor: DateExtractor,
    data_normalizer: DataNormalizationPort,
    validate_publication_year: Callable[[object], int | None],
    valid_date_patterns: Sequence[re.Pattern[str]],
    month_map: dict[str, int],
) -> dict[str, object]:
    """Extract normalized publication date fields from PubMed XML."""
    del pubmed_data
    journal = article.find(".//Journal")
    journal_issue = journal.find("JournalIssue") if journal is not None else None
    pub_date_node = journal_issue.find("PubDate") if journal_issue is not None else None
    raw_pub_date, raw_year = DateExtractor.extract_date(pub_date_node)
    validated_year = validate_publication_year(raw_year)

    pub_date = (
        raw_pub_date
        if is_valid_date_format(raw_pub_date, valid_date_patterns)
        else None
    )
    raw_epub_date = DateExtractor.extract_article_date(article, "Electronic")
    epub_date = (
        raw_epub_date
        if is_valid_date_format(raw_epub_date, valid_date_patterns)
        else None
    )

    pub_month, pub_day = parse_month_day(
        pub_date_node,
        date_extractor=date_extractor,
        month_map=month_map,
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
        "publication_date": compute_publication_date(
            data_normalizer=data_normalizer,
            epub_date=epub_date,
            pub_date=pub_date,
            year=validated_year,
        ),
        "publication_year": validated_year,
        "date_completed": date_completed,
        "date_revised": date_revised,
    }


__all__ = [
    "build_authors_with_affiliations",
    "compute_publication_date",
    "extract_date_data",
    "extract_journal_data",
    "is_valid_date_format",
    "parse_month",
    "parse_month_day",
    "process_structured_affiliations",
]
