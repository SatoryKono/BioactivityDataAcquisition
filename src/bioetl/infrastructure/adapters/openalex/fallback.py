"""Fallback search utilities for OpenAlex DOI resolution.

Provides title-based search fallback when DOI resolution fails.
Supports three-phase fallback strategy:
- Phase 2: Title fallback for unresolved DOIs
- Phase 3: Title-only lookup for entries without DOIs
"""

from __future__ import annotations

__all__ = ["OpenAlexTitleFallbackHandler"]


from typing import TYPE_CHECKING

from bioetl.infrastructure.adapters.common import BaseTitleFallbackHandler, titles_match

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from bioetl.domain.ports import LoggerPort
    from bioetl.domain.types import JsonDict


class OpenAlexTitleFallbackHandler(BaseTitleFallbackHandler):
    """Handles fallback search by title when DOI lookup fails.

    Extracts fallback logic to reduce main class size and cyclomatic complexity.
    Uses title matching to validate search results and reduce false positives.
    Uses provider_prefix="openalex" for auto-generated event names.
    """

    def __init__(
        self,
        logger: LoggerPort,
        search_fn: Callable[[str, int], Awaitable[list[JsonDict]]],
    ) -> None:
        """Initialize fallback handler.

        Args:
            logger: Logger port for structured logging.
            search_fn: Async function to search works by title.
        """
        super().__init__(logger, provider_prefix="openalex")
        self._search_fn = search_fn

    async def _search_by_title(
        self, title: str
    ) -> JsonDict | None:  # Any: untyped API JSON record
        """Search for work by title using OpenAlex API.

        Validates results using title matching to reduce false positives.
        Iterates through candidates to find the best match.

        Args:
            title: Publication title to search for.

        Returns:
            Work record if found and title matches, None otherwise.
        """
        candidates = await self._search_fn(title, 3)
        if not candidates:
            return None

        # Iterate through candidates to find a match
        for result in candidates:
            found_title = result.get("title", "")
            if found_title and titles_match(title, found_title):
                return result

        # Fallback: check if any candidate has no title (rare edge case)
        # Only return if we haven't found a match yet
        for result in candidates:
            if not result.get("title"):
                return result

        return None
