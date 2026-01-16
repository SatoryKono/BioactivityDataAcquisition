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

from bioetl.domain.normalization import (
    extract_first_string,
    format_date_parts,
    parse_page_range,
)
from bioetl.domain.value_objects import PublicationYear


def extract_authors(publication: dict[str, Any]) -> list[str]:
    """Extract author names in 'given family' format.

    CrossRef stores author information in an "author" array with
    "given" and "family" fields for each author.

    Args:
        publication: CrossRef publication record.

    Returns:
        List of author names in "given family" format.

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
    return authors


def extract_year(publication: dict[str, Any]) -> int | None:
    """Extract publication year from date-parts.

    Tries published-print, then published-online, then issued.
    Validates using PublicationYear Value Object for consistent range checking.

    Args:
        publication: CrossRef publication record.

    Returns:
        Publication year if valid (1800-2100), None otherwise.

    Example:
        >>> extract_year({"published-print": {"date-parts": [[2023, 6, 15]]}})
        2023
        >>> extract_year({"issued": {"date-parts": [[2021]]}})
        2021
        >>> extract_year({})
        None

    """
    for date_field in ["published-print", "published-online", "issued"]:
        date_info = publication.get(date_field, {})
        date_parts = date_info.get("date-parts", [[]])
        if date_parts and date_parts[0] and len(date_parts[0]) > 0:
            raw_year = date_parts[0][0]
            if isinstance(raw_year, int):
                year_vo = PublicationYear.from_raw(raw_year)
                if year_vo:
                    return year_vo.value
    return None


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
        url: str | None = licenses[0].get("URL")
        return url
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

    Parses page range string (e.g., "123-145") into first_page and last_page.

    Args:
        publication: CrossRef publication record.

    Returns:
        Dictionary with volume, issue, first_page, last_page fields.

    Example:
        >>> extract_page_info({
        ...     "volume": "42",
        ...     "issue": "3",
        ...     "page": "123-145"
        ... })
        {'volume': '42', 'issue': '3', 'first_page': '123', 'last_page': '145'}
        >>> extract_page_info({"page": "42"})
        {'volume': None, 'issue': None, 'first_page': '42', 'last_page': None}
        >>> extract_page_info({})
        {'volume': None, 'issue': None, 'first_page': None, 'last_page': None}

    """
    first_page, last_page = parse_page_range(publication.get("page"))
    return {
        "volume": publication.get("volume"),
        "issue": publication.get("issue"),
        "first_page": first_page,
        "last_page": last_page,
    }


def extract_dates(publication: dict[str, Any]) -> dict[str, Any]:
    """Extract publication dates from date-parts fields.

    Formats date-parts [[year, month?, day?]] to ISO date strings.

    Args:
        publication: CrossRef publication record.

    Returns:
        Dictionary with published_print, published_online fields (ISO format).

    Example:
        >>> extract_dates({
        ...     "published-print": {"date-parts": [[2023, 6, 15]]},
        ...     "published-online": {"date-parts": [[2023, 5]]}
        ... })
        {'published_print': '2023-06-15', 'published_online': '2023-05'}
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
