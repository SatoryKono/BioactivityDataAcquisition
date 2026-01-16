"""Fallback search utilities for CrossRef DOI resolution.

Provides title-based search fallback when DOI resolution fails.
Supports three-phase fallback strategy:
- Phase 2: Title fallback for unresolved DOIs
- Phase 3: Title-only lookup for entries without DOIs
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bioetl.infrastructure.adapters.common import BaseTitleFallbackHandler, titles_match

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable

    from bioetl.domain.ports import LoggerPort


# Re-export titles_match for backwards compatibility
__all__ = ["TitleFallbackHandler", "titles_match"]


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

    @property
    def _event_title_only_attempt(self) -> str:
        """Return log event name for title-only lookup attempt."""
        return "crossref_title_only_attempt"

    @property
    def _event_title_only_success(self) -> str:
        """Return log event name for successful title-only lookup."""
        return "crossref_title_only_success"

    @property
    def _event_title_only_not_found(self) -> str:
        """Return log event name for failed title-only lookup."""
        return "crossref_title_only_not_found"

    def _process_found_result(
        self, result: dict[str, Any], original_doi: str
    ) -> dict[str, Any]:
        """Add lookup method metadata to found publication.

        Args:
            result: The found publication record.
            original_doi: The DOI that was originally searched.

        Returns:
            Publication with _lookup_method and _original_doi added.
        """
        result["_lookup_method"] = "title_fallback"
        result["_original_doi"] = original_doi
        return result

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
