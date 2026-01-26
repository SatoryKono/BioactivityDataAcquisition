"""Fallback search utilities for OpenAlex DOI resolution.

Provides title-based search fallback when DOI resolution fails.
Supports three-phase fallback strategy:
- Phase 2: Title fallback for unresolved DOIs
- Phase 3: Title-only lookup for entries without DOIs
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from bioetl.infrastructure.adapters.common import BaseTitleFallbackHandler, titles_match

if TYPE_CHECKING:
    from collections.abc import Callable

    from bioetl.domain.ports import LoggerPort


class TitleFallbackHandler(BaseTitleFallbackHandler):
    """Handles fallback search by title when DOI lookup fails.

    Extracts fallback logic to reduce main class size and cyclomatic complexity.
    Uses title matching to validate search results and reduce false positives.
    Uses provider_prefix="openalex" for auto-generated event names.
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
        super().__init__(logger, provider_prefix="openalex")
        self._search_fn = search_fn

    async def _search_by_title(self, title: str) -> dict[str, Any] | None:
        """Search for work by title using OpenAlex API.

        Validates results using title matching to reduce false positives.

        Args:
            title: Publication title to search for.

        Returns:
            Work record if found and title matches, None otherwise.
        """
        result = await self._search_fn(title, 3)
        if result is None:
            return None

        # Validate title match to reduce false positives
        found_title = result.get("title", "")
        if found_title and titles_match(title, found_title):
            return cast(dict[str, Any], result)

        # If no title in result, return it anyway
        if not found_title:
            return cast(dict[str, Any], result)

        return None
