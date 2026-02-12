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

from typing import Any

from bioetl.application.pipelines.crossref.author_extractors import (
    extract_author_details,
    extract_author_orcids,
)
from bioetl.application.pipelines.crossref.reference_extractors import (
    extract_references,
)
from bioetl.domain.normalization import (
    extract_first_string,
    format_date_parts,
    parse_page_range,
)

# Re-exports for backward compatibility
__all__ = [
    "extract_author_details",
    "extract_author_orcids",
    "extract_author_ormolecule_ids",
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


# Backward-compatible alias (legacy name preserved for tests/older callers)
def extract_author_ormolecule_ids(publication: dict[str, Any]) -> list[str]:
    return extract_author_orcids(publication)


def extract_authors(publication: dict[str, Any]) -> list[str]:
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
    authors = []
    for author in publication.get("author", []):
        given = author.get("given", "").strip()
        family = author.get("family", "").strip()
        if given and family:
            authors.append(f"{given} {family}")
        elif family:
            authors.append(family)
        elif given:
            authors.append(given)
        elif name := author.get("name", "").strip():
            # Organizational author (e.g., "World Health Organization")
            authors.append(name)
    return authors


def extract_affiliations(publication: dict[str, Any]) -> list[str]:
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


def extract_license_url(publication: dict[str, Any]) -> str | None:
    """Extract first license URL from publication.

    CrossRef may provide multiple licenses; this returns the first URL.

    Args:
        publication: CrossRef publication record.

    Returns:
        First license URL or None if not available.

    Example:
        >>> extract_license_url({
        ...     "license": [{"URL": "https://creativecommons.org/licenses/by/4.0/"}]
        ... })
        'https://creativecommons.org/licenses/by/4.0/'
        >>> extract_license_url({"license": []})
        None
        >>> extract_license_url({})
        None

    """
    licenses = publication.get("license", [])
    if licenses and len(licenses) > 0:
        return licenses[0].get("URL")
    return None


def extract_journal_info(publication: dict[str, Any]) -> dict[str, Any]:
    """Extract journal information from publication.

    Extracts journal name (container-title), ISSN list, and publisher.

    Args:
        publication: CrossRef publication record.

    Returns:
        Dictionary with journal, issn, publisher fields.

    Example:
        >>> info = extract_journal_info({
        ...     "container-title": ["Nature", "Nature Publishing Group"],
        ...     "ISSN": ["0028-0836", "1476-4687"],
        ...     "publisher": "Springer Nature"
        ... })
        >>> info["journal"]
        'Nature'
        >>> info["issn"]
        ['0028-0836', '1476-4687']
        >>> extract_journal_info({})
        {'journal': None, 'issn': [], 'publisher': None}

    """
    return {
        "journal": extract_first_string(publication.get("container-title")),
        "issn": publication.get("ISSN", []),
        "publisher": publication.get("publisher"),
    }


def extract_page_info(publication: dict[str, Any]) -> dict[str, Any]:
    """Extract pagination information from publication.

    Parses page range string (e.g., "123-145") into page_first and page_last.

    Args:
        publication: CrossRef publication record.

    Returns:
        Dictionary with volume, issue, page_first, page_last fields.

    Example:
        >>> extract_page_info({
        ...     "volume": "42",
        ...     "issue": "3",
        ...     "page": "123-145"
        ... })
        {'volume': '42', 'issue': '3', 'page_first': '123', 'page_last': '145'}
        >>> extract_page_info({"page": "42"})
        {'volume': None, 'issue': None, 'page_first': '42', 'page_last': None}
        >>> extract_page_info({})
        {'volume': None, 'issue': None, 'page_first': None, 'page_last': None}

    """
    first_page, last_page = parse_page_range(publication.get("page"))
    return {
        "volume": publication.get("volume"),
        "issue": publication.get("issue"),
        "page_first": first_page,
        "page_last": last_page,
    }


def extract_dates(publication: dict[str, Any]) -> dict[str, Any]:
    """Extract publication dates from date-parts fields.

    Formats date-parts [[year, month?, day?]] to ISO date strings using
    end-of-period normalization for partial dates:
    - [[year, month, day]] -> "YYYY-MM-DD"
    - [[year, month]] -> "YYYY-MM-DD" (last day of month)
    - [[year]] -> "YYYY-12-31" (last day of year)

    Args:
        publication: CrossRef publication record.

    Returns:
        Dictionary with published_print, published_online fields (ISO format).

    Example:
        >>> extract_dates({
        ...     "published-print": {"date-parts": [[2023, 6, 15]]},
        ...     "published-online": {"date-parts": [[2023, 5]]}
        ... })
        {'published_print': '2023-06-15', 'published_online': '2023-05-31'}
        >>> extract_dates({})
        {'published_print': None, 'published_online': None}

    """
    published_print = publication.get("published-print", {})
    published_online = publication.get("published-online", {})

    return {
        "published_print": format_date_parts(
            published_print.get("date-parts")
            if isinstance(published_print, dict)
            else None
        ),
        "published_online": format_date_parts(
            published_online.get("date-parts")
            if isinstance(published_online, dict)
            else None
        ),
    }


def extract_content_domain(publication: dict[str, Any]) -> dict[str, Any]:
    """Extract content-domain metadata.

    CrossRef content-domain indicates licensing/access restrictions
    and Crossmark participation.

    Args:
        publication: CrossRef publication record.

    Returns:
        Dictionary with content_domain_domains, content_domain_crossmark_restriction.

    Example:
        >>> extract_content_domain({
        ...     "content-domain": {"domain": ["nature.com"], "crossmark-restriction": True}
        ... })
        {'content_domain_domains': ['nature.com'], 'content_domain_crossmark_restriction': True}
        >>> extract_content_domain({})
        {'content_domain_domains': [], 'content_domain_crossmark_restriction': None}

    """
    content_domain = publication.get("content-domain", {})
    if not isinstance(content_domain, dict):
        content_domain = {}

    return {
        "content_domain_domains": content_domain.get("domain", []) or [],
        "content_domain_crossmark_restriction": content_domain.get(
            "crossmark-restriction"
        ),
    }


def extract_issn_by_type(publication: dict[str, Any]) -> dict[str, Any]:
    """Extract ISSN values by type (print/electronic).

    Parses the issn-type array to separate print and electronic ISSNs.
    Takes first occurrence of each type if duplicates exist.

    Args:
        publication: CrossRef publication record.

    Returns:
        Dictionary with issn_print and issn_electronic.

    Example:
        >>> extract_issn_by_type({
        ...     "issn-type": [
        ...         {"value": "0006-291X", "type": "print"},
        ...         {"value": "1090-2104", "type": "electronic"}
        ...     ]
        ... })
        {'issn_print': '0006-291X', 'issn_electronic': '1090-2104'}
        >>> extract_issn_by_type({})
        {'issn_print': None, 'issn_electronic': None}

    """
    issn_type_list = publication.get("issn-type", [])
    if not isinstance(issn_type_list, list):
        return {"issn_print": None, "issn_electronic": None}

    issn_print: str | None = None
    issn_electronic: str | None = None

    for item in issn_type_list:
        if not isinstance(item, dict):
            continue
        issn_value = item.get("value")
        issn_kind = item.get("type")

        if issn_kind == "print" and issn_print is None:
            issn_print = issn_value
        elif issn_kind == "electronic" and issn_electronic is None:
            issn_electronic = issn_value

    return {
        "issn_print": issn_print,
        "issn_electronic": issn_electronic,
    }


def extract_published_date(publication: dict[str, Any]) -> str | None:
    """Extract 'published' date (canonical publication date).

    CrossRef's 'published' field is the preferred publication date,
    distinct from published-print and published-online which indicate
    specific publication events.

    Args:
        publication: CrossRef publication record.

    Returns:
        ISO date string (YYYY-MM-DD) or None.

    Example:
        >>> extract_published_date({"published": {"date-parts": [[2023, 6, 15]]}})
        '2023-06-15'
        >>> extract_published_date({"published": {"date-parts": [[2023]]}})
        '2023-12-31'
        >>> extract_published_date({})
        None

    """
    published = publication.get("published", {})
    if not isinstance(published, dict):
        return None

    return format_date_parts(published.get("date-parts"))
