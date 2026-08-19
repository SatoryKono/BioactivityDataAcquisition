# src/bioetl/application/pipelines/semanticscholar/extractors.py
"""Field extraction functions for Semantic Scholar records.

Provides pure functions for extracting and normalizing fields from
Semantic Scholar API responses.

Split into submodules per audit-package-structure-2026-02-07:
- _page_parsing: Volume/issue and page range parsing
- _author_extractors: Author name, ID, ORCID, h-index, affiliation extraction
"""

from __future__ import annotations

# Re-export from submodules for backward compatibility
from bioetl.application.pipelines.semanticscholar._author_extractors import (
    extract_affiliations,
    extract_author_h_indices,
    extract_author_ids,
    extract_author_orcids,
    extract_author_s2_ids,
    extract_authors,
)
from bioetl.application.pipelines.semanticscholar._page_parsing import (
    parse_page_range,
    parse_volume_issue,
)
from bioetl.domain.normalization.open_access import (
    OA_STATUS_REGISTRY as OA_STATUS_SET,
)
from bioetl.domain.normalization.open_access import (
    normalize_governed_oa_status as normalize_oa_status,
)
from bioetl.domain.types import JsonDict


def extract_external_ids(
    external_ids: JsonDict | None,  # Any: raw S2 API JSON
) -> JsonDict:  # Any: raw S2 API JSON
    """Extract all external identifiers from S2 response.

    Args:
        external_ids: Dict of external IDs from S2 response.

    Returns:
        Dict with normalized keys: doi, pmid, pmmolecule_id, arxiv, corpus_id, mag, dblp, acl.

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
        "pmmolecule_id": external_ids.get("PMCID") or external_ids.get("PubMedCentral"),
        "arxiv": external_ids.get("ArXiv"),
        "corpus_id": external_ids.get("CorpusId"),
        "mag": external_ids.get("MAG"),
        "dblp": external_ids.get("DBLP"),
        "acl": external_ids.get("ACL"),
    }


def extract_citation_contexts(
    citations: list[JsonDict]  # Any: raw S2 API JSON
    | None,
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


def extract_journal_info(
    journal: JsonDict  # Any: raw S2 API JSON
    | None,
    venue: str | None,
) -> JsonDict:  # Any: raw S2 API JSON
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
        {
        ...   'journal_name': 'Nature', 'volume': '629', 'issue': None,
        ...   'page_range': '123-130', 'page_first': '123', 'page_last': '130'
        ... }
        >>> journal = {"name": "J Med Chem", "volume": "32 4", "pages": "737-9"}
        >>> extract_journal_info(journal, None)
        {
        ...   'journal_name': 'J Med Chem', 'volume': '32', 'issue': '4',
        ...   'page_range': '737-9', 'page_first': '737', 'page_last': '739'
        ... }

    """
    if journal:
        raw_volume = journal.get("volume")
        raw_pages = journal.get("pages")

        # Parse volume/issue from combined string
        volume, issue = parse_volume_issue(raw_volume)

        # Parse page range with abbreviation expansion
        first_page, last_page = parse_page_range(raw_pages)

        # Clean pages string (strip whitespace/newlines)
        if isinstance(raw_pages, str) and raw_pages:
            pages = raw_pages.strip()
        elif raw_pages not in (None, ""):
            pages = str(raw_pages)
        else:
            pages = None

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


def extract_open_access_info(
    is_open_access: bool | None,
    open_access_pdf: JsonDict  # Any: raw S2 API JSON
    | None,
) -> JsonDict:  # Any: raw S2 API JSON
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


def extract_tldr(
    tldr: JsonDict | None,  # Any: raw S2 API JSON
) -> str | None:
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


__all__ = [
    "OA_STATUS_SET",
    "extract_affiliations",
    "extract_author_h_indices",
    "extract_author_ids",
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
]
