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


# Valid OA status values (normalized to lowercase for consistency with OpenAlex)
VALID_OA_STATUS_VALUES = {"gold", "green", "hybrid", "bronze", "closed"}


def normalize_oa_status(status: str | None) -> str | None:
    """Normalize OA status to lowercase.

    Converts OA status values to lowercase for consistency with OpenAlex.
    Returns None for invalid or unknown status values.

    Args:
        status: Raw OA status string (may be uppercase, mixed case, or None).

    Returns:
        Normalized lowercase status if valid, None otherwise.

    Example:
        >>> normalize_oa_status("GOLD")
        'gold'
        >>> normalize_oa_status("Green")
        'green'
        >>> normalize_oa_status("unknown")
        None
        >>> normalize_oa_status(None)
        None

    """
    if status is None:
        return None
    normalized = status.lower().strip()
    return normalized if normalized in VALID_OA_STATUS_VALUES else None


def extract_open_access_info(
    is_open_access: bool | None,
    open_access_pdf: dict[str, Any] | None,
) -> dict[str, Any]:
    """Extract open access information with normalized status.

    Extracts OA information from S2 API response and normalizes the status
    to lowercase for consistency with OpenAlex data.

    Args:
        is_open_access: Boolean flag from S2.
        open_access_pdf: PDF info object from S2.

    Returns:
        Dict with is_oa (bool), url (str|None), oa_status (str|None).
        If is_open_access is False or None and no OA PDF, oa_status is "closed".

    Example:
        >>> oa_pdf = {"url": "https://example.com/paper.pdf", "status": "GREEN"}
        >>> extract_open_access_info(True, oa_pdf)
        {'is_oa': True, 'url': 'https://...', 'oa_status': 'green'}
        >>> extract_open_access_info(False, None)
        {'is_oa': False, 'url': None, 'oa_status': 'closed'}

    """
    # Determine if open access
    is_oa = is_open_access or False

    # Extract URL and status from PDF info
    url: str | None = None
    raw_status: str | None = None

    if open_access_pdf:
        url = open_access_pdf.get("url")
        raw_status = open_access_pdf.get("status")

    # Normalize status to lowercase
    oa_status = normalize_oa_status(raw_status)

    # If not open access and no status, set to "closed"
    if not is_oa and oa_status is None:
        oa_status = "closed"

    return {
        "is_oa": is_oa,
        "url": url,
        "oa_status": oa_status,
    }


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
