# src/bioetl/application/pipelines/semanticscholar/extractors.py
"""Field extraction functions for Semantic Scholar records.

Provides pure functions for extracting and normalizing fields from
Semantic Scholar API responses.
"""

from __future__ import annotations

from typing import Any

from bioetl.domain.validation import validate_year_range


def extract_external_ids(external_ids: dict[str, Any] | None) -> dict[str, Any]:
    """Extract all external identifiers from S2 response.

    Args:
        external_ids: Dict of external IDs from S2 response.

    Returns:
        Dict with normalized keys: doi, pmid, pmcid, arxiv, corpus_id, mag, acl.

    Example:
        >>> ids = {"DOI": "10.1038/...", "PubMed": "12345678", "CorpusId": 123}
        >>> extract_external_ids(ids)
        {'doi': '10.1038/...', 'pmid': '12345678', 'corpus_id': 123, ...}

    """
    if not external_ids:
        return {}

    return {
        "doi": external_ids.get("DOI"),
        "pmid": external_ids.get("PubMed"),
        "pmcid": external_ids.get("PMCID") or external_ids.get("PubMedCentral"),
        "arxiv": external_ids.get("ArXiv"),
        "corpus_id": external_ids.get("CorpusId"),
        "mag": external_ids.get("MAG"),
        "acl": external_ids.get("ACL"),
    }


def extract_authors(authors: list[dict[str, Any]] | None) -> list[str]:
    """Extract author display names from authors list.

    Args:
        authors: List of author objects from S2.

    Returns:
        List of author names.

    Example:
        >>> authors = [{"authorId": "123", "name": "John Doe"}]
        >>> extract_authors(authors)
        ['John Doe']

    """
    if not authors:
        return []

    result = []
    for author in authors:
        name = author.get("name")
        if name:
            result.append(name)
    return result


def extract_journal_info(
    journal: dict[str, Any] | None,
    venue: str | None,
) -> dict[str, Any]:
    """Extract journal information.

    Args:
        journal: Journal object from S2 response.
        venue: Venue string (fallback if journal is empty).

    Returns:
        Dict with journal_name, volume, pages.

    Example:
        >>> journal = {"name": "Nature", "volume": "629", "pages": "123-130"}
        >>> extract_journal_info(journal, "Nature")
        {'journal_name': 'Nature', 'volume': '629', 'pages': '123-130'}

    """
    if journal:
        return {
            "journal_name": journal.get("name") or venue,
            "volume": journal.get("volume"),
            "pages": journal.get("pages"),
        }
    return {
        "journal_name": venue,
        "volume": None,
        "pages": None,
    }


def extract_open_access_info(
    is_open_access: bool | None,
    open_access_pdf: dict[str, Any] | None,
) -> dict[str, Any]:
    """Extract open access information.

    Args:
        is_open_access: Boolean flag from S2.
        open_access_pdf: PDF info object from S2.

    Returns:
        Dict with is_open_access, url, status.

    Example:
        >>> oa_pdf = {"url": "https://example.com/paper.pdf", "status": "GREEN"}
        >>> extract_open_access_info(True, oa_pdf)
        {'is_open_access': True, 'url': 'https://...', 'status': 'GREEN'}

    """
    result: dict[str, Any] = {
        "is_open_access": is_open_access or False,
        "url": None,
        "status": None,
    }

    if open_access_pdf:
        result["url"] = open_access_pdf.get("url")
        result["status"] = open_access_pdf.get("status")

    return result


def extract_tldr(tldr: dict[str, Any] | None) -> str | None:
    """Extract AI-generated summary from tldr field.

    Args:
        tldr: TLDR object from S2 response.

    Returns:
        Summary text or None.

    Example:
        >>> tldr = {"model": "tldr@v2.0.0", "text": "This paper presents..."}
        >>> extract_tldr(tldr)
        'This paper presents...'

    """
    if not tldr:
        return None
    return tldr.get("text")


def extract_fields_of_study(
    fields_of_study: list[str] | None,
    max_count: int = 10,
) -> list[str]:
    """Extract fields of study.

    Args:
        fields_of_study: List of field names from S2.
        max_count: Maximum fields to extract.

    Returns:
        List of field names (capped at max_count).

    Example:
        >>> fields = ["Biology", "Medicine", "Genetics"]
        >>> extract_fields_of_study(fields, max_count=2)
        ['Biology', 'Medicine']

    """
    if not fields_of_study:
        return []
    return fields_of_study[:max_count]


def validate_year(year: int | None) -> int | None:
    """Validate publication year using domain validation.

    Delegates to domain.validation.validate_year_range() with
    Semantic Scholar-specific minimum year of 1500.

    Args:
        year: Year from S2 response.

    Returns:
        Year if valid (1500-2100), None otherwise.

    """
    if year is None:
        return None
    if validate_year_range(year, min_year=1500):
        return year
    return None
