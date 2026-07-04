"""Author data extraction for Semantic Scholar records.

Pure functions for extracting author names, IDs, ORCIDs, h-indices,
and affiliations from S2 API responses.
Split from extractors.py per audit-package-structure-2026-02-07.
"""

from __future__ import annotations

from bioetl.domain.types import JsonDict


def extract_authors(
    authors: list[JsonDict] | None,  # Any: untyped API JSON record
) -> list[str]:  # Any: untyped API JSON record
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


def extract_author_ids(
    authors: list[JsonDict] | None,  # Any: untyped API JSON record
) -> list[str]:  # Any: untyped API JSON record
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


def extract_author_s2_ids(
    authors: list[JsonDict] | None,  # Any: untyped API JSON record
) -> list[str]:  # Any: untyped API JSON record
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


def extract_author_orcids(
    authors: list[JsonDict] | None,  # Any: untyped API JSON record
) -> list[str]:  # Any: untyped API JSON record
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


def extract_author_h_indices(
    authors: list[JsonDict] | None,  # Any: untyped API JSON record
) -> list[int | None]:  # Any: untyped API JSON record
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


def extract_affiliations(
    authors: list[JsonDict] | None,  # Any: untyped API JSON record
) -> list[str]:  # Any: untyped API JSON record
    """Extract affiliations from authors list.


    Semantic Scholar authors may have affiliations as a list of strings.

    Args:
        authors: List of author objects from S2.

    Returns:
        List of unique affiliation strings (sorted).

    Example:
        >>> authors = [
        ...     {"name": "John", "affiliations": ["Univ A"]},
        ...     {"name": "Jane", "affiliations": ["Univ B", "Univ A"]},
        ... ]
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
