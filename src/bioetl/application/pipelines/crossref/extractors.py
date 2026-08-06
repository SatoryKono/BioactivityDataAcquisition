"""Field extraction functions for CrossRef records.

Provides pure functions for extracting and normalizing fields from
CrossRef Works API responses.

These functions are:
- Stateless and pure (no side effects)
- Unit testable in isolation
- Reusable across different transformation contexts

Note: Uses domain normalization functions and Value Objects per REFACTOR-004.
"""

from __future__ import annotations

from bioetl.application.pipelines.crossref._publication_field_extractors import (
    extract_content_domain,
    extract_dates,
    extract_issn_by_type,
    extract_journal_info,
    extract_license_url,
    extract_page_info,
    extract_published_date,
)
from bioetl.application.pipelines.crossref.author_extractors import (
    extract_author_details,
    extract_author_orcids,
)
from bioetl.application.pipelines.crossref.reference_extractors import (
    extract_references,
)
from bioetl.domain.types import JsonDict

# Re-exports for backward compatibility
__all__ = [
    "extract_author_details",
    "extract_author_orcids",
    "extract_authors",
    "extract_content_domain",
    "extract_dates",
    "extract_issn_by_type",
    "extract_journal_info",
    "extract_license_url",
    "extract_page_info",
    "extract_published_date",
    "extract_references",
]


def extract_authors(
    publication: JsonDict,  # Any: untyped API JSON record
) -> list[str]:  # Any: untyped JSON fragment from Crossref API
    """Extract author names from CrossRef publication.

    CrossRef stores author information in an "author" array with:
    - Personal authors: "given" and "family" fields
    - Organizational authors: "name" field only (e.g., "World Health Organization")

    Args:
        publication: CrossRef publication record.

    Returns:
        List of author names (personal: "given family", org: "name").

    Example:
        >>> extract_authors({
        ...     "author": [
        ...         {"given": "John", "family": "Doe"},
        ...         {"given": "Jane", "family": "Smith"},
        ...     ]
        ... })
        ['John Doe', 'Jane Smith']
        >>> extract_authors({"author": [{"family": "Anonymous"}]})
        ['Anonymous']
        >>> extract_authors({"author": [{"name": "World Health Organization"}]})
        ['World Health Organization']
        >>> extract_authors({})
        []

    """
    authors: list[str] = []
    raw_authors = publication.get("author", [])
    # Match extract_affiliations: only iterate list-of-dict author payloads.
    if not isinstance(raw_authors, list):
        return authors
    for author in raw_authors:
        if not isinstance(author, dict):
            continue
        given_raw = author.get("given", "")
        family_raw = author.get("family", "")
        given = given_raw.strip() if isinstance(given_raw, str) else ""
        family = family_raw.strip() if isinstance(family_raw, str) else ""
        if given and family:
            authors.append(f"{given} {family}")
        elif family:
            authors.append(family)
        elif given:
            authors.append(given)
        else:
            name_raw = author.get("name", "")
            if isinstance(name_raw, str) and (name := name_raw.strip()):
                # Organizational author (e.g., "World Health Organization")
                authors.append(name)
    return authors


def extract_affiliations(
    publication: JsonDict,  # Any: untyped API JSON record
) -> list[str]:  # Any: untyped JSON fragment from Crossref API
    """Extract unique affiliations from CrossRef publication.

    CrossRef affiliations are often nested inside author objects.
    Format: author -> affiliation -> [{'name': 'University...'}] or string list.

    Args:
        publication: CrossRef publication record.

    Returns:
        List of unique affiliation strings (sorted).

    Example:
        >>> extract_affiliations({
        ...     "author": [
        ...         {"affiliation": [{"name": "University A"}]},
        ...         {"affiliation": [{"name": "University B"}, {"name": "University A"}]}
        ...     ]
        ... })
        ['University A', 'University B']
    """
    affiliations: set[str] = set()
    for author in publication.get("author", []):
        if not isinstance(author, dict):
            continue

        aff_list = author.get("affiliation", [])
        if not isinstance(aff_list, list):
            continue

        for aff in aff_list:
            name = None
            if isinstance(aff, dict):
                name = aff.get("name")
            elif isinstance(aff, str):
                name = aff

            if name and isinstance(name, str):
                affiliations.add(name.strip())

    return sorted(affiliations)
