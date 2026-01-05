"""Field extraction functions for OpenAlex records.

Contains pure functions for extracting and normalizing fields
from OpenAlex Works API responses.

These functions are:
- Stateless and pure (no side effects)
- Unit testable in isolation
- Reusable across different transformation contexts
"""

from __future__ import annotations

from typing import Any


def extract_doi(doi_url: str | None) -> str | None:
    """Extract bare DOI from OpenAlex DOI URL.

    OpenAlex stores DOIs as full URLs (e.g., "https://doi.org/10.1038/s41586-024-07487-w").
    This function extracts just the DOI identifier.

    Args:
        doi_url: DOI URL from OpenAlex (e.g., "https://doi.org/10.1038/...").

    Returns:
        Bare DOI (e.g., "10.1038/s41586-024-07487-w") or None if not available.

    Example:
        >>> extract_doi("https://doi.org/10.1038/s41586-024-07487-w")
        '10.1038/s41586-024-07487-w'
        >>> extract_doi(None)
        None
    """
    if not doi_url:
        return None
    if doi_url.startswith("https://doi.org/"):
        return doi_url[16:]
    if doi_url.startswith("http://doi.org/"):
        return doi_url[15:]
    if doi_url.startswith("doi:"):
        return doi_url[4:]
    return doi_url


def extract_openalex_id(openalex_url: str | None) -> str | None:
    """Extract OpenAlex ID from OpenAlex URL.

    OpenAlex stores IDs as full URLs (e.g., "https://openalex.org/W2148763428").
    This function extracts just the Work ID.

    Args:
        openalex_url: OpenAlex URL (e.g., "https://openalex.org/W2148763428").

    Returns:
        OpenAlex Work ID (e.g., "W2148763428") or None if not available.

    Example:
        >>> extract_openalex_id("https://openalex.org/W2148763428")
        'W2148763428'
        >>> extract_openalex_id(None)
        None
    """
    if not openalex_url:
        return None
    if "/" in openalex_url:
        return openalex_url.split("/")[-1]
    return openalex_url


def extract_authors(authorships: list[dict[str, Any]]) -> list[str]:
    """Extract author display names from authorships.

    OpenAlex stores author information in an "authorships" array with
    nested "author" objects containing display names.

    Args:
        authorships: List of authorship objects from OpenAlex.

    Returns:
        List of author display names.

    Example:
        >>> extract_authors([
        ...     {"author": {"display_name": "John Doe"}},
        ...     {"author": {"display_name": "Jane Smith"}},
        ... ])
        ['John Doe', 'Jane Smith']
    """
    authors = []
    for authorship in authorships:
        author = authorship.get("author", {})
        if not isinstance(author, dict):
            continue
        name = author.get("display_name")
        if name and isinstance(name, str):
            authors.append(name.strip())
    return authors


def extract_concepts(
    concepts: list[dict[str, Any]], max_count: int = 10
) -> list[str]:
    """Extract top concept names from concepts list.

    OpenAlex provides concepts sorted by relevance score.
    This function extracts the display names of the top concepts.

    Args:
        concepts: List of concept objects (sorted by score).
        max_count: Maximum concepts to extract (default 10).

    Returns:
        List of concept display names.

    Example:
        >>> extract_concepts([
        ...     {"display_name": "Chemistry", "score": 0.9},
        ...     {"display_name": "Biology", "score": 0.7},
        ... ])
        ['Chemistry', 'Biology']
    """
    result = []
    for concept in concepts[:max_count]:
        if not isinstance(concept, dict):
            continue
        name = concept.get("display_name")
        if name and isinstance(name, str):
            result.append(name.strip())
    return result


def extract_journal_info(primary_location: dict[str, Any] | None) -> dict[str, Any]:
    """Extract journal information from primary_location.

    OpenAlex stores source information in "primary_location.source".
    This function extracts journal name, ISSN, and publisher.

    Args:
        primary_location: Primary location object from OpenAlex.

    Returns:
        Dictionary with journal_name, issn, publisher.

    Example:
        >>> extract_journal_info({
        ...     "source": {
        ...         "display_name": "Nature",
        ...         "issn_l": "0028-0836",
        ...         "host_organization_name": "Springer Nature"
        ...     }
        ... })
        {'journal_name': 'Nature', 'issn': '0028-0836', 'publisher': 'Springer Nature'}
    """
    if not primary_location or not isinstance(primary_location, dict):
        return {"journal_name": None, "issn": None, "publisher": None}

    source = primary_location.get("source", {}) or {}
    if not isinstance(source, dict):
        return {"journal_name": None, "issn": None, "publisher": None}

    return {
        "journal_name": source.get("display_name"),
        "issn": source.get("issn_l"),
        "publisher": source.get("host_organization_name"),
    }


def reconstruct_abstract(inverted_index: dict[str, list[int]] | None) -> str | None:
    """Reconstruct abstract from OpenAlex inverted index.

    OpenAlex stores abstracts as inverted index format for storage efficiency:
    {"word": [positions]}.
    This function reconstructs the original text.

    Args:
        inverted_index: Dict mapping words to position lists.

    Returns:
        Reconstructed abstract text or None if not available.

    Example:
        >>> reconstruct_abstract({
        ...     "This": [0],
        ...     "is": [1, 4],
        ...     "an": [2],
        ...     "example": [3],
        ...     "abstract": [5]
        ... })
        'This is an example is abstract'
    """
    if not inverted_index or not isinstance(inverted_index, dict):
        return None

    # Build position -> word mapping
    word_positions: list[tuple[int, str]] = []
    for word, positions in inverted_index.items():
        if not isinstance(positions, list):
            continue
        for pos in positions:
            if isinstance(pos, int):
                word_positions.append((pos, word))

    if not word_positions:
        return None

    # Sort by position and join
    word_positions.sort(key=lambda x: x[0])
    return " ".join(word for _, word in word_positions)


def extract_open_access_info(open_access: dict[str, Any] | None) -> dict[str, Any]:
    """Extract Open Access information from open_access object.

    Args:
        open_access: Open access object from OpenAlex.

    Returns:
        Dictionary with is_oa and oa_status.

    Example:
        >>> extract_open_access_info({"is_oa": True, "oa_status": "gold"})
        {'is_oa': True, 'oa_status': 'gold'}
    """
    if not open_access or not isinstance(open_access, dict):
        return {"is_oa": None, "oa_status": None}

    return {
        "is_oa": open_access.get("is_oa"),
        "oa_status": open_access.get("oa_status"),
    }
