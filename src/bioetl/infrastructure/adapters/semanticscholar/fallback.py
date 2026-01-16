"""Fallback search utilities for Semantic Scholar DOI resolution.

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


class TitleFallbackHandler(BaseTitleFallbackHandler):
    """Handles fallback search by title when DOI lookup fails.

    Extracts fallback logic from the Semantic Scholar provider to reduce
    class size and cyclomatic complexity while providing unified
    three-phase fallback strategy.
    """

    def __init__(
        self,
        logger: LoggerPort,
        search_fn: Callable[[str], AsyncIterator[dict[str, Any]]],
    ) -> None:
        """Initialize fallback handler.

        Args:
            logger: Logger port for structured logging.
            search_fn: Async generator function to search publications by title.
        """
        super().__init__(logger)
        self._search_fn = search_fn

    @property
    def _event_no_fallback_title(self) -> str:
        """Return log event name for missing fallback title."""
        return "semanticscholar_no_fallback_title"

    @property
    def _event_fallback_attempt(self) -> str:
        """Return log event name for fallback attempt."""
        return "semanticscholar_title_fallback_attempt"

    @property
    def _event_fallback_success(self) -> str:
        """Return log event name for successful fallback."""
        return "semanticscholar_title_fallback_success"

    @property
    def _event_fallback_not_found(self) -> str:
        """Return log event name for failed fallback."""
        return "semanticscholar_title_fallback_not_found"

    @property
    def _event_title_only_attempt(self) -> str:
        """Return log event name for title-only lookup attempt."""
        return "semanticscholar_title_only_attempt"

    @property
    def _event_title_only_success(self) -> str:
        """Return log event name for successful title-only lookup."""
        return "semanticscholar_title_only_success"

    @property
    def _event_title_only_not_found(self) -> str:
        """Return log event name for failed title-only lookup."""
        return "semanticscholar_title_only_not_found"

    async def _search_by_title(self, title: str) -> dict[str, Any] | None:
        """Search for publication by title.

        Uses the injected search function to search Semantic Scholar
        and validates the result using title matching.

        Args:
            title: Publication title to search for.

        Returns:
            First matching publication or None.
        """
        try:
            async for record in self._search_fn(title):
                # Validate title match to reduce false positives
                found_title = record.get("title", "")
                if found_title and titles_match(title, found_title):
                    return record
                # If no title in record, return first result
                if not found_title:
                    return record
        except Exception as e:
            self._logger.debug(
                "semanticscholar_title_search_failed",
                title=title[:50],
                error=str(e),
            )
        return None

    def _get_result_identifier(self, result: dict[str, Any]) -> tuple[str, str]:
        """Return Semantic Scholar paper ID for logging."""
        return ("found_paper_id", str(result.get("paperId", "unknown")))

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
