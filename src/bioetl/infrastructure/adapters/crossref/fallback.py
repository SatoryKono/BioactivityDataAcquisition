"""Fallback search utilities for CrossRef DOI resolution.

Provides title-based search fallback when DOI resolution fails.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bioetl.infrastructure.adapters.common import BaseTitleFallbackHandler

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


class TitleFallbackHandler(BaseTitleFallbackHandler):
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
        super().__init__(logger)
        self._search_fn = search_fn

    @property
    def _event_no_fallback_title(self) -> str:
        """Return log event name for missing fallback title."""
        return "crossref_no_fallback_title"

    @property
    def _event_fallback_attempt(self) -> str:
        """Return log event name for fallback attempt."""
        return "crossref_title_fallback_attempt"

    @property
    def _event_fallback_success(self) -> str:
        """Return log event name for successful fallback."""
        return "crossref_title_fallback_success"

    @property
    def _event_fallback_not_found(self) -> str:
        """Return log event name for failed fallback."""
        return "crossref_title_fallback_not_found"

    async def _search_by_title(self, title: str) -> dict[str, Any] | None:
        """Search for a publication by title.

        Args:
            title: Publication title to search for.

        Returns:
            First relevant publication or None.
        """
        return await self.search_by_title(title)

    def _get_result_identifier(self, result: dict[str, Any]) -> tuple[str, str]:
        """Return CrossRef DOI for logging."""
        return ("found_doi", str(result.get("DOI", "unknown")))

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
