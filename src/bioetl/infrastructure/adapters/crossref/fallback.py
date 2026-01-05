"""Fallback search utilities for CrossRef DOI resolution.

Provides title-based search fallback when DOI resolution fails.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable

    from bioetl.domain.ports import LoggerPort


def titles_match(query_title: str, found_title: str, threshold: float = 0.8) -> bool:
    """Check if titles match (case-insensitive, normalized).

    Args:
        query_title: The title we're searching for.
        found_title: The title found in CrossRef.
        threshold: Unused, reserved for future fuzzy matching.

    Returns:
        True if titles match, False otherwise.
    """
    q = query_title.lower().strip()
    f = found_title.lower().strip()

    # Exact match
    if q == f:
        return True

    # Substring match (title may be truncated)
    return q in f or f in q


class TitleFallbackHandler:
    """Handles fallback search by title when DOI lookup fails.

    Extracts fallback logic to reduce main class size and cyclomatic complexity.
    """

    def __init__(
        self,
        logger: LoggerPort,
        search_fn: Callable[[str, int], AsyncIterator[dict[str, Any]]],
    ) -> None:
        """Initialize fallback handler.

        Args:
            logger: Logger port for structured logging.
            search_fn: Async function to search publications by query.
        """
        self._logger = logger
        self._search_fn = search_fn

    async def search_by_title(
        self,
        title: str,
        limit: int = 3,
    ) -> dict[str, Any] | None:
        """Search for a publication by title.

        Args:
            title: Publication title to search for.
            limit: Maximum results to check for relevance.

        Returns:
            First relevant publication or None.
        """
        # Clean title for search (CrossRef limit)
        clean_title = title.strip()[:200]

        try:
            async for publication in self._search_fn(
                f'title:"{clean_title}"',
                limit,
            ):
                # Check relevance (title must match)
                pub_titles = publication.get("title", [])
                found_title = pub_titles[0] if pub_titles else ""
                if titles_match(clean_title, found_title):
                    return publication
        except Exception as e:
            self._logger.debug(
                "crossref_title_search_failed",
                title=clean_title[:50],
                error=str(e),
            )

        return None

    def _get_fallback_title(
        self, doi: str, normalized_doi: str, fallback_mapping: dict[str, str]
    ) -> str | None:
        """Get fallback title for a DOI from mapping."""
        return fallback_mapping.get(doi) or fallback_mapping.get(normalized_doi)

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
        """Process DOIs not found via batch fetch using title fallback."""
        for doi in dois:
            if limit and fetched >= limit:
                return
            normalized_doi = (normalize_fn(doi) or "").lower()
            if normalized_doi in found_dois:
                continue
            title = self._get_fallback_title(doi, normalized_doi, fallback_mapping)
            if not title:
                self._logger.debug("crossref_no_fallback_title", doi=doi)
                continue
            self._logger.info(
                "crossref_title_fallback_attempt",
                doi=doi,
                title=self._truncate_title(title),
            )
            publication = await self.search_by_title(title)
            if publication:
                self._logger.info(
                    "crossref_title_fallback_success",
                    original_doi=doi,
                    found_doi=publication.get("DOI"),
                    title=title[:50],
                )
                yield publication
                fetched += 1
            else:
                self._logger.warning(
                    "crossref_title_fallback_not_found", doi=doi, title=title[:50]
                )
