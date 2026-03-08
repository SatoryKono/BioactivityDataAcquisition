"""OpenAlex query parameter builders."""

from __future__ import annotations

from collections.abc import Iterable


def build_openalex_base_params(mailto: str) -> dict[str, str]:
    """Build base OpenAlex parameters with polite-pool mailto.

    Args:
        mailto: Email address for the OpenAlex polite pool.

    Returns:
        Dictionary containing the mailto parameter for polite pool access.
    """
    return {"mailto": mailto}


def build_openalex_search_params(
    *,
    mailto: str,
    query: str,
    cursor: str,
    per_page: int,
) -> dict[str, str]:
    """Build query search parameters for `/works` cursor pagination.

    Args:
        mailto: Email address for the OpenAlex polite pool.
        query: Search query string to filter works.
        cursor: Pagination cursor from the previous page response.
        per_page: Number of results to request per page.

    Returns:
        Dictionary of query parameters for cursor-based search requests.
    """
    params = build_openalex_base_params(mailto)
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
    mailto: str,
    dois: Iterable[str],
) -> dict[str, str]:
    """Build DOI filter parameters for batch DOI lookup.

    Args:
        mailto: Email address for the OpenAlex polite pool.
        dois: Iterable of DOI strings to filter by in the batch request.

    Returns:
        Dictionary of query parameters with DOI pipe-separated filter for batch resolution.
    """
    normalized_dois = list(dois)
    doi_filter = "|".join(normalized_dois)
    params = build_openalex_base_params(mailto)
    params.update(
        {
            "filter": f"doi:{doi_filter}",
            "per-page": str(len(normalized_dois)),
        }
    )
    return params


def build_openalex_title_search_params(
    *,
    mailto: str,
    escaped_title: str,
    limit: int,
) -> dict[str, str]:
    """Build title search parameters for `title.search` lookup.

    Args:
        mailto: Email address for the OpenAlex polite pool.
        escaped_title: URL-safe escaped title string for the filter value.
        limit: Maximum number of results to request per page.

    Returns:
        Dictionary of query parameters for title-based search requests.
    """
    params = build_openalex_base_params(mailto)
    params.update(
        {
            "filter": f"title.search:{escaped_title}",
            "per-page": str(limit),
        }
    )
    return params


def build_openalex_health_probe_params(mailto: str) -> dict[str, str]:
    """Build minimal parameters for health probing.

    Args:
        mailto: Email address for the OpenAlex polite pool.

    Returns:
        Dictionary of minimal query parameters for the health probe request.
    """
    return {
        "per-page": "1",
        "mailto": mailto,
    }


__all__ = [
    "build_openalex_base_params",
    "build_openalex_doi_filter_params",
    "build_openalex_health_probe_params",
    "build_openalex_search_params",
    "build_openalex_title_search_params",
]
