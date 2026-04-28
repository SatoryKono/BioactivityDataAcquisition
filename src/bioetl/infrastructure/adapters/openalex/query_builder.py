"""OpenAlex query parameter builders."""

from __future__ import annotations

from collections.abc import Iterable


def build_openalex_base_params(
    mailto: str | None,
    api_key: str | None = None,
) -> dict[str, str]:
    """Build base OpenAlex parameters with API-key auth and optional mailto.

    Args:
        mailto: Optional email address retained for legacy request attribution.
        api_key: Optional OpenAlex API key.

    Returns:
        Dictionary containing OpenAlex authentication/contact parameters.
    """
    params: dict[str, str] = {}
    if api_key:
        params["api_key"] = api_key
    if mailto:
        params["mailto"] = mailto
    return params


def build_openalex_search_params(
    *,
    mailto: str | None,
    api_key: str | None = None,
    query: str,
    cursor: str,
    per_page: int,
) -> dict[str, str]:
    """Build query search parameters for `/works` cursor pagination.

    Args:
        mailto: Optional email address retained for legacy request attribution.
        api_key: Optional OpenAlex API key.
        query: Search query string to filter works.
        cursor: Pagination cursor from the previous page response.
        per_page: Number of results to request per page.

    Returns:
        Dictionary of query parameters for cursor-based search requests.
    """
    params = build_openalex_base_params(mailto, api_key=api_key)
    params.update(
        {
            "search": query,
            "cursor": cursor,
            "per-page": str(per_page),
        }
    )
    return params


def build_openalex_doi_filter_params(
    *,
    mailto: str | None,
    api_key: str | None = None,
    dois: Iterable[str],
) -> dict[str, str]:
    """Build DOI filter parameters for batch DOI lookup.

    Args:
        mailto: Optional email address retained for legacy request attribution.
        api_key: Optional OpenAlex API key.
        dois: Iterable of DOI strings to filter by in the batch request.

    Returns:
        Dictionary of query parameters with DOI pipe-separated filter for batch resolution.
    """
    normalized_dois = list(dois)
    doi_filter = "|".join(normalized_dois)
    params = build_openalex_base_params(mailto, api_key=api_key)
    params.update(
        {
            "filter": f"doi:{doi_filter}",
            "per-page": str(len(normalized_dois)),
        }
    )
    return params


def build_openalex_title_search_params(
    *,
    mailto: str | None,
    api_key: str | None = None,
    escaped_title: str,
    limit: int,
) -> dict[str, str]:
    """Build title search parameters for `title.search` lookup.

    Args:
        mailto: Optional email address retained for legacy request attribution.
        api_key: Optional OpenAlex API key.
        escaped_title: URL-safe escaped title string for the filter value.
        limit: Maximum number of results to request per page.

    Returns:
        Dictionary of query parameters for title-based search requests.
    """
    params = build_openalex_base_params(mailto, api_key=api_key)
    params.update(
        {
            "filter": f"title.search:{escaped_title}",
            "per-page": str(limit),
        }
    )
    return params


def build_openalex_health_probe_params(
    mailto: str | None,
    api_key: str | None = None,
) -> dict[str, str]:
    """Build minimal parameters for health probing.

    Args:
        mailto: Optional email address retained for legacy request attribution.
        api_key: Optional OpenAlex API key.

    Returns:
        Dictionary of minimal query parameters for the health probe request.
    """
    params = build_openalex_base_params(mailto, api_key=api_key)
    params["per-page"] = "1"
    return params


__all__ = [
    "build_openalex_base_params",
    "build_openalex_doi_filter_params",
    "build_openalex_health_probe_params",
    "build_openalex_search_params",
    "build_openalex_title_search_params",
]
