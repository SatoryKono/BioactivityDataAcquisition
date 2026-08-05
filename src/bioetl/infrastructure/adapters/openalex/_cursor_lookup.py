"""DOI batch and title-search helpers for OpenAlex cursor flow."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.adapters.openalex.query_builder import (
    build_openalex_doi_filter_params,
    build_openalex_title_search_params,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.openalex.query_execution import (
        OpenAlexQueryExecutor,
    )
    from bioetl.infrastructure.adapters.openalex.response_mapping import (
        OpenAlexResponseMapper,
    )

__all__ = [
    "fetch_works_by_dois",
    "normalize_openalex_dois",
    "search_works_by_title",
]


def normalize_openalex_dois(
    *,
    dois: list[str],
    normalize_doi: Callable[[str], str | None],
) -> list[str]:
    """Normalize and drop empty DOI values."""
    normalized_raw = [normalize_doi(item) for item in dois if item]
    return [doi for doi in normalized_raw if doi is not None]


async def fetch_works_by_dois(
    *,
    dois: list[str],
    mailto: str | None,
    api_key: str | None,
    normalize_doi: Callable[[str], str | None],
    query_executor: OpenAlexQueryExecutor,
    response_mapper: OpenAlexResponseMapper,
    logger: LoggerPort,
) -> list[BronzeRecord]:
    """Resolve DOI batch and return records list."""
    normalized = normalize_openalex_dois(dois=dois, normalize_doi=normalize_doi)
    if not normalized:
        return []

    params = build_openalex_doi_filter_params(
        mailto=mailto,
        api_key=api_key,
        dois=normalized,
    )
    logger.debug("openalex_batch_doi_request", doi_count=len(normalized))
    payload = await query_executor.request_works_payload(params)
    results = response_mapper.extract_results(payload)
    if len(results) < len(normalized):
        logger.info(
            "openalex_batch_partial_results",
            requested=len(normalized),
            found=len(results),
            hit_rate=round(len(results) / len(normalized) * 100, 1),
        )
    return results


async def search_works_by_title(
    *,
    title: str,
    limit: int,
    mailto: str | None,
    api_key: str | None,
    escape_title_for_search: Callable[[str], str],
    query_executor: OpenAlexQueryExecutor,
    response_mapper: OpenAlexResponseMapper,
    logger: LoggerPort,
    runtime_errors: tuple[type[Exception], ...],
    title_search_cache: dict[tuple[str, int], list[BronzeRecord]],
    title_search_cache_size: int,
) -> list[BronzeRecord]:
    """Search by title with in-memory cache and graceful runtime fallback."""
    normalized_title = title.strip()
    cache_key = (normalized_title.casefold(), limit)
    cached = title_search_cache.get(cache_key)
    if cached is not None:
        return [dict(item) for item in cached]

    params = build_openalex_title_search_params(
        mailto=mailto,
        api_key=api_key,
        escaped_title=escape_title_for_search(normalized_title[:200]),
        limit=limit,
    )
    logger.debug("openalex_title_search", title=title[:50])
    try:
        payload = await query_executor.request_works_payload(params)
        results = response_mapper.extract_results(payload)
    except runtime_errors as error:
        logger.debug(
            "openalex_title_search_failed",
            title=title[:50],
            error=str(error),
        )
        title_search_cache[cache_key] = []
        return []

    cached_results = [dict(item) for item in results]
    title_search_cache[cache_key] = cached_results
    if len(title_search_cache) > title_search_cache_size:
        oldest_key = next(iter(title_search_cache))
        del title_search_cache[oldest_key]
    return [dict(item) for item in cached_results]
