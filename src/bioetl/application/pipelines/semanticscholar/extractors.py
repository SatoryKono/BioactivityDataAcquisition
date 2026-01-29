# src/bioetl/application/pipelines/semanticscholar/extractors.py
"""Field extraction functions for Semantic Scholar records.

Provides pure functions for extracting and normalizing fields from
Semantic Scholar API responses.
"""

from __future__ import annotations

import re
from typing import Any

from bioetl.domain.config import ValidationConfig
from bioetl.domain.value_objects import PublicationYear

# Semantic Scholar-specific config with min_year=1500 for historical publications
_SS_VALIDATION_CONFIG = ValidationConfig(min_publication_year=1500)


# =============================================================================
# Volume/Issue Parsing
# =============================================================================

# Patterns for parsing combined volume/issue strings from S2 API.
# The API sometimes returns both values in the volume field (e.g., "32 4").
_VOLUME_ISSUE_PATTERNS = [
    # "32 4" → vol=32, issue=4 (space-separated, common S2 format)
    re.compile(r"^(\d+)\s+(\d+)$"),
    # "32(4)" or "32 (4)" → vol=32, issue=4
    re.compile(r"^(\d+)\s*\((\d+)\)$"),
    # "Vol. 32, No. 4" or "Vol 32 No 4"
    re.compile(r"^[Vv]ol\.?\s*(\d+)[,\s]+[Nn]o\.?\s*(\d+)$"),
    # "32:4" → vol=32, issue=4
    re.compile(r"^(\d+):(\d+)$"),
]


def parse_volume_issue(volume_str: str | None) -> tuple[str | None, str | None]:
    """Parse volume string that may contain issue number.

    Semantic Scholar API sometimes returns combined volume/issue in the
    volume field (e.g., "32 4" for volume 32, issue 4).

    Args:
        volume_str: Raw volume string from S2 API.

    Returns:
        Tuple of (volume, issue). Issue is None if not embedded.

    Examples:
        >>> parse_volume_issue("32 4")
        ('32', '4')
        >>> parse_volume_issue("523")
        ('523', None)
        >>> parse_volume_issue("40(3)")
        ('40', '3')
        >>> parse_volume_issue(None)
        (None, None)

    """
    if not volume_str:
        return (None, None)

    cleaned = volume_str.strip()
    if not cleaned:
        return (None, None)

    # Try each pattern for combined volume/issue
    for pattern in _VOLUME_ISSUE_PATTERNS:
        match = pattern.match(cleaned)
        if match:
            return (match.group(1), match.group(2))

    # No issue found - return volume as-is
    return (cleaned, None)


# =============================================================================
# Page Range Parsing
# =============================================================================


def _extract_digits(s: str) -> str:
    """Extract digits from string."""
    return "".join(c for c in s if c.isdigit())


def _extract_prefix(s: str) -> str:
    """Extract non-digit prefix from string."""
    return "".join(c for c in s if not c.isdigit())


def _calculate_expanded_page_number(
    first_num: int,
    last_num: int,
    last_digits_len: int,
) -> int:
    """Calculate the expanded page number from first page and abbreviated last page.

    Args:
        first_num: parsed integer of first page.
        last_num: parsed integer of last page (abbreviated).
        last_digits_len: number of digits in the abbreviated last page.

    Returns:
        Expanded integer page number.
    """
    divisor = 10**last_digits_len
    expanded = (first_num // divisor) * divisor + last_num

    # Handle rollover case: "199-3" should be "199-203", not "199-193"
    if expanded < first_num:
        expanded += divisor
    return expanded


def _expand_abbreviated_page(first_page: str, tmp_last_page: str) -> str:
    """Expand abbreviated last page number.

    Academic publishing often abbreviates page ranges:
    - "737-9" means 737-739 (not 737-9)
    - "737-39" means 737-739
    - "199-3" means 199-203 (rollover case)

    Algorithm:
    1. If tmp_last_page has >= digits than first_page, return as-is
    2. Otherwise: last_page = (first_page // 10^n2) * 10^n2 + tmp_last_page
    3. Handle rollover: if expanded < first_page, add 10^n2

    Args:
        first_page: First page (e.g., "737")
        tmp_last_page: Potentially abbreviated last page (e.g., "9", "39", "839")

    Returns:
        Expanded last page string.

    """
    # Extract numeric parts only for calculation
    first_digits = _extract_digits(first_page)
    last_digits = _extract_digits(tmp_last_page)

    # If either is non-numeric, return as-is (e.g., "S1-S5")
    if not first_digits or not last_digits:
        return tmp_last_page

    n1 = len(first_digits)  # digits in first_page
    n2 = len(last_digits)  # digits in tmp_last_page

    # If last page has same or more digits, it's a full number
    if n2 >= n1:
        return tmp_last_page

    # Expand abbreviated page number
    first_num = int(first_digits)
    last_num = int(last_digits)

    expanded = _calculate_expanded_page_number(first_num, last_num, n2)

    # Preserve any prefix from tmp_last_page (e.g., "S" in "S5")
    prefix = _extract_prefix(tmp_last_page)
    return f"{prefix}{expanded}" if prefix else str(expanded)


def parse_page_range(pages_str: str | None) -> tuple[str | None, str | None]:
    """Parse page range with abbreviated last page expansion.

    Academic publishing often abbreviates page ranges:
    - "737-9" means 737-739 (not 737-9)
    - "737-39" means 737-739
    - "737-839" means 737-839 (full number, no expansion)

    Also handles whitespace, en-dashes (–), and em-dashes (—).

    Args:
        pages_str: Raw pages string (e.g., "737-9", "123-145").

    Returns:
        Tuple of (first_page, last_page). Both are strings or None.

    Examples:
        >>> parse_page_range("737-9")
        ('737', '739')
        >>> parse_page_range("737-39")
        ('737', '739')
        >>> parse_page_range("737-839")
        ('737', '839')
        >>> parse_page_range("123")
        ('123', None)
        >>> parse_page_range("S1-S5")
        ('S1', 'S5')

    """
    if not pages_str:
        return (None, None)

    cleaned = pages_str.strip()
    if not cleaned:
        return (None, None)

    # Normalize various dash types to hyphen
    # EN DASH (U+2013) and EM DASH (U+2014) → HYPHEN-MINUS (U+002D)
    cleaned = cleaned.replace("\u2013", "-").replace("\u2014", "-")

    # Split on "-" (only first occurrence)
    parts = cleaned.split("-", 1)

    first_page = parts[0].strip()
    if not first_page:
        return (None, None)

    # No range separator - single page
    if len(parts) == 1:
        return (first_page, None)

    tmp_last_page = parts[1].strip()
    if not tmp_last_page:
        return (first_page, None)

    # Expand abbreviated page number
    last_page = _expand_abbreviated_page(first_page, tmp_last_page)

    return (first_page, last_page)


def extract_external_ids(external_ids: dict[str, Any] | None) -> dict[str, Any]:
    """Extract all external identifiers from S2 response.

    Args:
        external_ids: Dict of external IDs from S2 response.

    Returns:
        Dict with normalized keys: doi, pmid, pmcid, arxiv, corpus_id, mag, dblp, acl.

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
        "dblp": external_ids.get("DBLP"),
        "acl": external_ids.get("ACL"),
    }


def extract_authors(authors: list[dict[str, Any]] | None) -> list[str]:
    """Extract author display names from authors list.

    Filters out None, empty strings, and whitespace-only names.

    Args:
        authors: List of author objects from S2.

    Returns:
        List of author names (non-empty, stripped).

    Example:
        >>> authors = [{"authorId": "123", "name": "John Doe"}]
        >>> extract_authors(authors)
        ['John Doe']
        >>> authors = [{"name": "  "}, {"name": ""}, {"name": None}]
        >>> extract_authors(authors)
        []

    """
    if not authors:
        return []

    result = []
    for author in authors:
        name = author.get("name")
        if name and name.strip():
            result.append(name.strip())
    return result


def extract_author_ids(authors: list[dict[str, Any]] | None) -> list[str]:
    """Extract author IDs from authors list.

    Args:
        authors: List of author objects from S2.

    Returns:
        List of authorId strings.

    Example:
        >>> authors = [{"authorId": "123", "name": "John"}, {"authorId": "456", "name": "Jane"}]
        >>> extract_author_ids(authors)
        ['123', '456']
    """
    if not authors:
        return []

    result = []
    for author in authors:
        aid = author.get("authorId")
        if aid:
            result.append(str(aid))
    return result


def extract_author_s2_ids(authors: list[dict[str, Any]] | None) -> list[str]:
    """Extract Semantic Scholar author IDs from authors list.

    Extracts the 40-character hex S2 author IDs for author-level analytics
    and disambiguation.

    Args:
        authors: List of author objects from S2 API.

    Returns:
        List of S2 author IDs (non-empty, in order of authorship).

    Example:
        >>> authors = [
        ...     {"authorId": "1234567890abcdef1234567890abcdef12345678", "name": "John"},
        ...     {"authorId": None, "name": "Jane"},
        ...     {"authorId": "abcdef1234567890abcdef1234567890abcdef12", "name": "Bob"},
        ... ]
        >>> extract_author_s2_ids(authors)
        ['1234567890abcdef1234567890abcdef12345678', 'abcdef1234567890abcdef1234567890abcdef12']

    """
    if not authors:
        return []

    result = []
    for author in authors:
        author_id = author.get("authorId")
        if author_id and isinstance(author_id, str) and author_id.strip():
            result.append(author_id.strip())
    return result


def extract_author_orcids(authors: list[dict[str, Any]] | None) -> list[str]:
    """Extract ORCID identifiers from authors list.

    ORCID (Open Researcher and Contributor ID) provides persistent digital
    identifiers for researchers. This extracts ORCIDs from the externalIds
    field of each author.

    Args:
        authors: List of author objects from S2 API with externalIds.

    Returns:
        List of ORCID identifiers (non-empty, in order of authorship).
        Empty string placeholder is used for authors without ORCID.

    Example:
        >>> authors = [
        ...     {"name": "John", "externalIds": {"ORCID": "0000-0001-2345-6789"}},
        ...     {"name": "Jane", "externalIds": None},
        ...     {"name": "Bob", "externalIds": {"ORCID": "0000-0002-3456-7890"}},
        ... ]
        >>> extract_author_orcids(authors)
        ['0000-0001-2345-6789', '', '0000-0002-3456-7890']

    """
    if not authors:
        return []

    result = []
    for author in authors:
        external_ids = author.get("externalIds")
        orcid = ""
        if external_ids and isinstance(external_ids, dict):
            orcid_val = external_ids.get("ORCID")
            if orcid_val and isinstance(orcid_val, str) and orcid_val.strip():
                orcid = orcid_val.strip()
        result.append(orcid)
    return result


def extract_author_h_indices(authors: list[dict[str, Any]] | None) -> list[int | None]:
    """Extract h-index values from authors list.

    The h-index is a metric for research impact. This extracts h-index
    values for each author from the S2 API response.

    Args:
        authors: List of author objects from S2 API with hIndex field.

    Returns:
        List of h-index values (int or None for each author, in order).

    Example:
        >>> authors = [
        ...     {"name": "John", "hIndex": 45},
        ...     {"name": "Jane", "hIndex": None},
        ...     {"name": "Bob", "hIndex": 23},
        ... ]
        >>> extract_author_h_indices(authors)
        [45, None, 23]

    """
    if not authors:
        return []

    result: list[int | None] = []
    for author in authors:
        h_index = author.get("hIndex")
        if h_index is not None and isinstance(h_index, int) and h_index >= 0:
            result.append(h_index)
        else:
            result.append(None)
    return result


def extract_citation_contexts(
    citations: list[dict[str, Any]] | None,
    max_contexts: int = 100,
) -> list[str]:
    """Extract citation context sentences from citations/references.

    When requesting citation or reference details with the 'contexts' field,
    S2 returns the actual sentences where a paper is cited. This is invaluable
    for understanding how research is used and for citation sentiment analysis.

    Args:
        citations: List of citation/reference objects from S2 API.
        max_contexts: Maximum number of context sentences to extract.

    Returns:
        List of citation context sentences (non-empty, stripped).

    Example:
        >>> citations = [
        ...     {"paperId": "abc123", "contexts": ["The method in [1] shows...", "As shown by [1]..."]},
        ...     {"paperId": "def456", "contexts": ["Building on [2]..."]},
        ... ]
        >>> extract_citation_contexts(citations, max_contexts=3)
        ['The method in [1] shows...', 'As shown by [1]...', 'Building on [2]...']

    """
    if not citations:
        return []

    result: list[str] = []
    for citation in citations:
        contexts = citation.get("contexts")
        if not contexts or not isinstance(contexts, list):
            continue

        for context in contexts:
            if len(result) >= max_contexts:
                return result
            if context and isinstance(context, str) and context.strip():
                result.append(context.strip())

    return result


def extract_affiliations(authors: list[dict[str, Any]] | None) -> list[str]:
    """Extract affiliations from authors list.

    Semantic Scholar authors may have affiliations as a list of strings.

    Args:
        authors: List of author objects from S2.

    Returns:
        List of unique affiliation strings (sorted).

    Example:
        >>> authors = [{"name": "John", "affiliations": ["Univ A"]}, {"name": "Jane", "affiliations": ["Univ B", "Univ A"]}]
        >>> extract_affiliations(authors)
        ['Univ A', 'Univ B']
    """
    if not authors:
        return []

    affiliations: set[str] = set()
    for author in authors:
        author_affs = author.get("affiliations")
        if not author_affs or not isinstance(author_affs, list):
            continue

        for aff in author_affs:
            if aff and isinstance(aff, str) and aff.strip():
                affiliations.add(aff.strip())

    return sorted(affiliations)


def extract_journal_info(
    journal: dict[str, Any] | None,
    venue: str | None,
) -> dict[str, Any]:
    """Extract journal information with volume/issue and page parsing.

    Parses combined volume/issue strings (e.g., "32 4" → volume=32, issue=4)
    and expands abbreviated page ranges (e.g., "737-9" → first_page=737, last_page=739).

    Args:
        journal: Journal object from S2 response.
        venue: Venue string (fallback if journal is empty).

    Returns:
        Dict with journal, volume, issue, page_range, page_first, page_last.

    Example:
        >>> journal = {"name": "Nature", "volume": "629", "pages": "123-130"}
        >>> extract_journal_info(journal, "Nature")
        {'journal_name': 'Nature', 'volume': '629', 'issue': None, 'page_range': '123-130', 'page_first': '123', 'page_last': '130'}
        >>> journal = {"name": "J Med Chem", "volume": "32 4", "pages": "737-9"}
        >>> extract_journal_info(journal, None)
        {'journal_name': 'J Med Chem', 'volume': '32', 'issue': '4', 'page_range': '737-9', 'page_first': '737', 'page_last': '739'}

    """
    if journal:
        raw_volume = journal.get("volume")
        raw_pages = journal.get("pages")

        # Parse volume/issue from combined string
        volume, issue = parse_volume_issue(raw_volume)

        # Parse page range with abbreviation expansion
        first_page, last_page = parse_page_range(raw_pages)

        # Clean pages string (strip whitespace/newlines)
        pages = raw_pages.strip() if raw_pages else None

        return {
            "journal": journal.get("name") or venue,
            "volume": volume,
            "issue": issue,
            "page_range": pages,
            "page_first": first_page,
            "page_last": last_page,
        }
    return {
        "journal": venue,
        "volume": None,
        "issue": None,
        "page_range": None,
        "page_first": None,
        "page_last": None,
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

    Semantic meaning of is_oa values:
    - True: Publication is confirmed open access
    - False: Publication is confirmed closed access
    - None: Open access status is unknown (API did not provide info)

    We preserve None to distinguish "unknown" from "closed" for downstream
    analytics. Converting None to False would misrepresent the data quality.

    Args:
        is_open_access: Boolean flag from S2 (True/False/None).
        open_access_pdf: PDF info object from S2.

    Returns:
        Dict with is_oa (bool|None), url (str|None), oa_status (str|None).
        - oa_status is "closed" only when is_oa is explicitly False
        - oa_status is None when is_oa is None (unknown) and no PDF status

    Example:
        >>> oa_pdf = {"url": "https://example.com/paper.pdf", "status": "GREEN"}
        >>> extract_open_access_info(True, oa_pdf)
        {'is_oa': True, 'url': 'https://...', 'oa_status': 'green'}
        >>> extract_open_access_info(False, None)
        {'is_oa': False, 'url': None, 'oa_status': 'closed'}
        >>> extract_open_access_info(None, None)
        {'is_oa': None, 'url': None, 'oa_status': None}

    """
    # Preserve is_open_access as-is: True, False, or None (unknown)
    # Do NOT convert None to False - they have different semantic meanings
    is_oa = is_open_access

    # Extract URL and status from PDF info
    url: str | None = None
    raw_status: str | None = None

    if open_access_pdf:
        url = open_access_pdf.get("url")
        raw_status = open_access_pdf.get("status")

    # Normalize status to lowercase
    oa_status = normalize_oa_status(raw_status)

    # Only set "closed" when is_oa is explicitly False (not None/unknown)
    # This preserves the distinction between "closed" and "unknown"
    if is_oa is False and oa_status is None:
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

    Filters out None and empty string elements from the list.

    Args:
        fields_of_study: List of field names from S2.
        max_count: Maximum fields to extract.

    Returns:
        List of non-empty field names (capped at max_count).

    Example:
        >>> fields = ["Biology", "Medicine", "Genetics"]
        >>> extract_fields_of_study(fields, max_count=2)
        ['Biology', 'Medicine']
        >>> fields = ["Biology", None, "", "Medicine"]
        >>> extract_fields_of_study(fields)
        ['Biology', 'Medicine']

    """
    if not fields_of_study:
        return []
    # Filter out None and empty strings, then cap at max_count
    return [f for f in fields_of_study if f and isinstance(f, str)][:max_count]


def validate_year(year: int | None) -> int | None:
    """Validate publication year using PublicationYear Value Object.

    Uses Semantic Scholar-specific ValidationConfig with min_year=1500
    to support historical publications.

    Args:
        year: Year from S2 response.

    Returns:
        Year if valid (1500-2100), None otherwise.

    """
    if year is None:
        return None
    year_vo = PublicationYear.from_raw(year, config=_SS_VALIDATION_CONFIG)
    return year_vo.value if year_vo else None


__all__ = [
    "VALID_OA_STATUS_VALUES",
    "extract_affiliations",
    "extract_author_h_indices",
    "extract_author_orcids",
    "extract_author_s2_ids",
    "extract_authors",
    "extract_citation_contexts",
    "extract_external_ids",
    "extract_fields_of_study",
    "extract_journal_info",
    "extract_open_access_info",
    "extract_tldr",
    "normalize_oa_status",
    "parse_page_range",
    "parse_volume_issue",
    "validate_year",
]
