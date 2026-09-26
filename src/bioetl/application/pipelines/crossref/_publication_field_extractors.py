"""Publication field extractors for CrossRef records."""

from __future__ import annotations

from bioetl.domain.normalization import (
    extract_first_string,
    format_date_parts,
    parse_page_range,
)
from bioetl.domain.types import JsonDict


def extract_license_url(
    publication: JsonDict,  # Any: untyped API JSON record
) -> str | None:
    """Extract first license URL from publication."""
    licenses = publication.get("license", [])
    # Crossref ``license`` is list-only; dict/str/None must not index or .get.
    if not isinstance(licenses, list) or not licenses:
        return None
    first = licenses[0]
    if not isinstance(first, dict):
        return None
    url = first.get("URL")
    return url if isinstance(url, str) and url.strip() else None


def extract_journal_info(
    publication: JsonDict,  # Any: untyped API JSON record
) -> JsonDict:
    """Extract journal information from publication."""
    issn_values = publication.get("ISSN", [])
    issn_list = issn_values if isinstance(issn_values, list) else []
    canonical_issn_list = issn_list or None
    return {
        "journal": extract_first_string(publication.get("container-title")),
        "issn": extract_first_string(issn_list),
        "issn_list": canonical_issn_list,
        "publisher": publication.get("publisher"),
    }


def extract_page_info(
    publication: JsonDict,  # Any: untyped API JSON record
) -> JsonDict:
    """Extract pagination information from publication."""
    first_page, last_page = parse_page_range(publication.get("page"))
    return {
        "volume": publication.get("volume"),
        "issue": publication.get("issue"),
        "page_first": first_page,
        "page_last": last_page,
    }


def extract_dates(
    publication: JsonDict,  # Any: untyped API JSON record
) -> JsonDict:
    """Extract publication dates from date-parts fields."""
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


def extract_content_domain(
    publication: JsonDict,  # Any: untyped API JSON record
) -> JsonDict:
    """Extract content-domain metadata."""
    content_domain = publication.get("content-domain", {})
    if not isinstance(content_domain, dict):
        content_domain = {}

    return {
        "content_domain_domains": content_domain.get("domain", []) or [],
        "content_domain_crossmark_restriction": content_domain.get(
            "crossmark-restriction"
        ),
    }


def extract_issn_by_type(
    publication: JsonDict,  # Any: untyped API JSON record
) -> JsonDict:
    """Extract ISSN values by type (print/electronic)."""
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


def extract_published_date(
    publication: JsonDict,  # Any: untyped API JSON record
) -> str | None:
    """Extract canonical publication date from CrossRef payload."""
    published = publication.get("published", {})
    if not isinstance(published, dict):
        return None

    return format_date_parts(published.get("date-parts"))
