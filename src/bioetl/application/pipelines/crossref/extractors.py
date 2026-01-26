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


def _normalize_orcid(orcid_value: str | None) -> str | None:
    """Normalize ORCID to ID-only format (without URL prefix).

    CrossRef may provide ORCID as full URL (https://orcid.org/0000-0001-2345-6789)
    or as ID only (0000-0001-2345-6789). This normalizes to ID-only format.

    Args:
        orcid_value: Raw ORCID value (URL or ID).

    Returns:
        ORCID ID (format: 0000-0000-0000-000X) or None if invalid.

    Example:
        >>> _normalize_orcid("https://orcid.org/0000-0001-2345-6789")
        '0000-0001-2345-6789'
        >>> _normalize_orcid("0000-0001-2345-6789")
        '0000-0001-2345-6789'
        >>> _normalize_orcid(None)
        None

    """
    if not orcid_value or not isinstance(orcid_value, str):
        return None

    orcid = orcid_value.strip()
    # Remove URL prefix if present
    if orcid.startswith("https://orcid.org/"):
        orcid = orcid[len("https://orcid.org/") :]
    elif orcid.startswith("http://orcid.org/"):
        orcid = orcid[len("http://orcid.org/") :]

    # Validate format: 0000-0000-0000-000X
    if len(orcid) == 19 and orcid[4] == "-" and orcid[9] == "-" and orcid[14] == "-":
        return orcid
    return None


def extract_author_details(publication: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract full author details from CrossRef publication.

    Extracts comprehensive author information including ORCID identifiers,
    institutional affiliations, and author sequence information.

    CrossRef author objects may contain:
    - given: First/given name
    - family: Last/family name
    - name: Organization name (for institutional authors)
    - ORCID: Persistent author identifier (URL or ID format)
    - authenticated-orcid: Whether ORCID is CrossRef-authenticated
    - sequence: 'first' or 'additional' (author order)
    - affiliation: Array of institution objects

    Args:
        publication: CrossRef publication record.

    Returns:
        List of author detail dictionaries with keys:
        - given: str | None
        - family: str | None
        - name: str | None (for organizations)
        - orcid: str | None (normalized to ID-only format)
        - authenticated_orcid: bool | None
        - sequence: str | None ('first' or 'additional')
        - affiliations: list[str] (institution names)

    Example:
        >>> extract_author_details({
        ...     "author": [{
        ...         "given": "John",
        ...         "family": "Doe",
        ...         "ORCID": "https://orcid.org/0000-0001-2345-6789",
        ...         "authenticated-orcid": True,
        ...         "sequence": "first",
        ...         "affiliation": [{"name": "Harvard University"}]
        ...     }]
        ... })  # doctest: +NORMALIZE_WHITESPACE
        [{'given': 'John', 'family': 'Doe', 'name': None,
          'orcid': '0000-0001-2345-6789', 'authenticated_orcid': True,
          'sequence': 'first', 'affiliations': ['Harvard University']}]

    """
    author_details: list[dict[str, Any]] = []

    for author in publication.get("author", []):
        if not isinstance(author, dict):
            continue

        given = author.get("given", "").strip() or None
        family = author.get("family", "").strip() or None
        org_name = author.get("name", "").strip() or None

        # Skip if no identifiable name
        if not given and not family and not org_name:
            continue

        # Normalize ORCID (remove URL prefix if present)
        orcid = _normalize_orcid(author.get("ORCID"))

        # Extract authenticated-orcid flag
        authenticated_orcid = author.get("authenticated-orcid")
        if authenticated_orcid is not None:
            authenticated_orcid = bool(authenticated_orcid)

        # Extract sequence (first/additional)
        sequence = author.get("sequence")
        if sequence and isinstance(sequence, str):
            sequence = sequence.strip().lower()
            if sequence not in ("first", "additional"):
                sequence = None
        else:
            sequence = None

        # Extract affiliations
        affiliations: list[str] = []
        aff_list = author.get("affiliation", [])
        if isinstance(aff_list, list):
            for aff in aff_list:
                aff_name = None
                if isinstance(aff, dict):
                    aff_name = aff.get("name")
                elif isinstance(aff, str):
                    aff_name = aff
                if aff_name and isinstance(aff_name, str):
                    aff_name = aff_name.strip()
                    if aff_name:
                        affiliations.append(aff_name)

        author_details.append(
            {
                "given": given,
                "family": family,
                "name": org_name,
                "orcid": orcid,
                "authenticated_orcid": authenticated_orcid,
                "sequence": sequence,
                "affiliations": affiliations,
            }
        )

    return author_details


def extract_author_orcids(publication: dict[str, Any]) -> list[str]:
    """Extract list of ORCID identifiers from CrossRef publication.

    Extracts and normalizes all ORCID identifiers from the author array.
    Only includes non-empty, valid ORCIDs (normalized to ID-only format).

    Args:
        publication: CrossRef publication record.

    Returns:
        List of ORCID IDs (format: 0000-0000-0000-000X), preserving author order.
        Authors without ORCID are not included.

    Example:
        >>> extract_author_orcids({
        ...     "author": [
        ...         {"given": "John", "family": "Doe",
        ...          "ORCID": "https://orcid.org/0000-0001-2345-6789"},
        ...         {"given": "Jane", "family": "Smith"},
        ...         {"given": "Bob", "family": "Wilson",
        ...          "ORCID": "0000-0002-3456-7890"}
        ...     ]
        ... })
        ['0000-0001-2345-6789', '0000-0002-3456-7890']
        >>> extract_author_orcids({})
        []

    """
    orcids: list[str] = []

    for author in publication.get("author", []):
        if not isinstance(author, dict):
            continue

        orcid = _normalize_orcid(author.get("ORCID"))
        if orcid:
            orcids.append(orcid)

    return orcids


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


def _clean_string(value: Any, lowercase: bool = False) -> str | None:
    """Clean and optionally lowercase a string value.

    Helper function for extract_references to reduce code repetition.

    Args:
        value: Value to clean (expected to be string or None).
        lowercase: Whether to convert to lowercase.

    Returns:
        Cleaned string or None if empty/invalid.

    """
    if not value or not isinstance(value, str):
        return None
    cleaned: str = value.strip()
    if not cleaned:
        return None
    return cleaned.lower() if lowercase else cleaned


def _parse_year(year_raw: Any) -> int | None:
    """Parse year from string or int value.

    Args:
        year_raw: Raw year value (string or int).

    Returns:
        Integer year or None if invalid.

    """
    if not year_raw:
        return None
    if isinstance(year_raw, int):
        return year_raw
    if isinstance(year_raw, str):
        year_str = year_raw.strip()
        if year_str.isdigit():
            return int(year_str)
    return None


def extract_references(publication: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract bibliographic references from CrossRef publication.

    Parses the 'reference' array containing citations to other works.
    This data is essential for citation network analysis and bibliometric studies.

    CrossRef reference objects may contain:
    - key: Unique reference identifier within the publication
    - DOI: DOI of the cited work (if resolved)
    - doi-asserted-by: Who asserted the DOI ('publisher' or 'crossref')
    - article-title: Title of the cited article
    - volume-title: Title of a book/volume (for book citations)
    - journal-title: Journal name
    - series-title: Series name (for book series)
    - author: First author name
    - year: Publication year (as string)
    - volume: Volume number
    - issue: Issue number
    - first-page: First page number
    - unstructured: Unstructured citation string (fallback)
    - ISSN: Journal ISSN
    - ISBN: Book ISBN

    Args:
        publication: CrossRef publication record.

    Returns:
        List of reference dictionaries with normalized keys.
        Each reference contains available bibliographic metadata.

    Example:
        >>> extract_references({
        ...     "reference": [{
        ...         "key": "ref1",
        ...         "DOI": "10.1000/xyz123",
        ...         "article-title": "Example Article",
        ...         "author": "Smith",
        ...         "year": "2020",
        ...         "journal-title": "Nature"
        ...     }]
        ... })  # doctest: +NORMALIZE_WHITESPACE
        [{'key': 'ref1', 'doi': '10.1000/xyz123', 'doi_asserted_by': None,
          'article_title': 'Example Article', 'volume_title': None,
          'journal_title': 'Nature', 'series_title': None, 'author': 'Smith',
          'year': 2020, 'volume': None, 'issue': None, 'first_page': None,
          'unstructured': None, 'issn': None, 'isbn': None}]
        >>> extract_references({})
        []

    """
    references: list[dict[str, Any]] = []

    for ref in publication.get("reference", []):
        if not isinstance(ref, dict):
            continue

        references.append(
            {
                "key": _clean_string(ref.get("key")),
                "doi": _clean_string(ref.get("DOI"), lowercase=True),
                "doi_asserted_by": _clean_string(
                    ref.get("doi-asserted-by"), lowercase=True
                ),
                "article_title": _clean_string(ref.get("article-title")),
                "volume_title": _clean_string(ref.get("volume-title")),
                "journal_title": _clean_string(ref.get("journal-title")),
                "series_title": _clean_string(ref.get("series-title")),
                "author": _clean_string(ref.get("author")),
                "year": _parse_year(ref.get("year")),
                "volume": _clean_string(ref.get("volume")),
                "issue": _clean_string(ref.get("issue")),
                "first_page": _clean_string(ref.get("first-page")),
                "unstructured": _clean_string(ref.get("unstructured")),
                "issn": _clean_string(ref.get("ISSN")),
                "isbn": _clean_string(ref.get("ISBN")),
            }
        )

    return references
