"""Fallback search utilities for OpenAlex DOI resolution.

Provides title-based search fallback when DOI resolution fails.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable

    from bioetl.domain.ports import LoggerPort


class TitleFallbackHandler:
    """Handles fallback search by title when DOI lookup fails.

    Extracts fallback logic to reduce main class size and cyclomatic complexity.
    """

    def __init__(
        self,
        logger: LoggerPort,
        search_fn: Callable[[str, int], Any],  # Coroutine returning dict | None
    ) -> None:
        """Initialize fallback handler.

        Args:
            logger: Logger port for structured logging.
            search_fn: Async function to search works by title.
        """
        self._logger = logger
        self._search_fn = search_fn

    def _get_fallback_title(
        self, doi: str, normalized_doi: str | None, fallback_mapping: dict[str, str]
    ) -> str | None:
        """Get fallback title for a DOI from mapping."""
        if normalized_doi:
            return fallback_mapping.get(doi) or fallback_mapping.get(normalized_doi)
        return fallback_mapping.get(doi)

    def _truncate_title(self, title: str, max_len: int = 50) -> str:
        """Truncate title for logging."""
        return title[:max_len] + "..." if len(title) > max_len else title

    async def process_missing_dois(
        self,
        dois: list[str],
        found_dois: set[str],
        fallback_mapping: dict[str, str],
        normalize_fn: Callable[[str], str | None],
        limit: int | None,
        fetched: int,
    ) -> AsyncIterator[dict[str, Any]]:
        """Process DOIs not found via batch fetch using title fallback.

        Args:
            dois: List of DOIs that were requested.
            found_dois: Set of DOIs that were successfully resolved (lowercase).
            fallback_mapping: Mapping {doi: title} for fallback search.
            normalize_fn: Function to normalize DOI strings.
            limit: Maximum total records to return.
            fetched: Number of records already fetched.

        Yields:
            Work records found via title search with _lookup_method set.
        """
        for doi in dois:
            if limit and fetched >= limit:
                return

            normalized_doi = (normalize_fn(doi) or "").lower()
            if normalized_doi in found_dois:
                continue

            title = self._get_fallback_title(doi, normalized_doi, fallback_mapping)
            if not title:
                self._logger.debug("openalex_no_fallback_title", doi=doi)
                continue

            self._logger.info(
                "openalex_title_fallback_attempt",
                doi=doi,
                title=self._truncate_title(title),
            )

            work = await self._search_fn(title, 3)
            if work:
                self._logger.info(
                    "openalex_title_fallback_success",
                    original_doi=doi,
                    found_id=work.get("id"),
                    title=title[:50],
                )
                work["_lookup_method"] = "title_fallback"
                work["_original_doi"] = doi
                yield work
                fetched += 1
            else:
                self._logger.warning(
                    "openalex_title_fallback_not_found",
                    doi=doi,
                    title=title[:50],
                )
