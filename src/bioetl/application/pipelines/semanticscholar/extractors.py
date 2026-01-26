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


# ArXiv ID patterns (validated based on arXiv documentation)
# Old format (before 2007): category/YYMMNNN (e.g., hep-ph/9912271, cs.AI/0001007)
# New format (since 2007): YYMM.NNNNN[vN] (e.g., 0704.0001, 2301.12345v2)
_ARXIV_OLD_PATTERN = re.compile(r"^[a-z-]+(\.[A-Z]{2})?/\d{7}(v\d+)?$", re.IGNORECASE)
_ARXIV_NEW_PATTERN = re.compile(r"^\d{4}\.\d{4,5}(v\d+)?$")


def sanitize_arxiv_id(arxiv_id: str | None) -> str | None:
    """Sanitize and validate ArXiv ID.

    Validates against known ArXiv ID formats:
    - Old format (pre-2007): category/YYMMNNN (e.g., "hep-ph/9912271")
    - New format (post-2007): YYMM.NNNNN[vN] (e.g., "2301.12345v2")

    Args:
        arxiv_id: Raw ArXiv ID from S2 response.

    Returns:
        Sanitized ArXiv ID if valid, None otherwise.

    Example:
        >>> sanitize_arxiv_id("2301.12345")
        '2301.12345'
        >>> sanitize_arxiv_id("hep-ph/9912271")
        'hep-ph/9912271'
        >>> sanitize_arxiv_id("invalid-id")
        None

    """
    if not arxiv_id or not isinstance(arxiv_id, str):
        return None

    cleaned = arxiv_id.strip()
    if not cleaned:
        return None

    # Match against known patterns
    if _ARXIV_NEW_PATTERN.match(cleaned) or _ARXIV_OLD_PATTERN.match(cleaned):
        return cleaned

    return None


# DBLP ID pattern: paths with components separated by "/"
# Examples: "conf/nips/SmithJ21", "journals/jmlr/SmithJ21", "books/daglib/0028988"
_DBLP_PATTERN = re.compile(r"^[a-z]+(/[a-zA-Z0-9_-]+)+$")


def sanitize_dblp_id(dblp_id: str | None) -> str | None:
    """Sanitize and validate DBLP ID.

    Validates DBLP IDs which follow a path-like format:
    - Conference: "conf/venue/AuthorYear" (e.g., "conf/nips/SmithJ21")
    - Journal: "journals/journal/AuthorYear" (e.g., "journals/jmlr/SmithJ21")
    - Book: "books/publisher/id" (e.g., "books/daglib/0028988")

    Args:
        dblp_id: Raw DBLP ID from S2 response.

    Returns:
        Sanitized DBLP ID if valid, None otherwise.

    Example:
        >>> sanitize_dblp_id("conf/nips/SmithJ21")
        'conf/nips/SmithJ21'
        >>> sanitize_dblp_id("journals/jmlr/SmithJ21")
        'journals/jmlr/SmithJ21'
        >>> sanitize_dblp_id("invalid")
        None

    """
    if not dblp_id or not isinstance(dblp_id, str):
        return None

    cleaned = dblp_id.strip()
    if not cleaned:
        return None

    # Match against DBLP path pattern
    if _DBLP_PATTERN.match(cleaned):
        return cleaned

    return None
