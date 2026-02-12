"""Fallback search utilities for OpenAlex DOI resolution.

Provides title-based search fallback when DOI resolution fails.
Supports three-phase fallback strategy:
- Phase 2: Title fallback for unresolved DOIs
- Phase 3: Title-only lookup for entries without DOIs
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from bioetl.infrastructure.adapters.common import (
    BaseAlternateIdFallbackHandler,
    BaseTitleFallbackHandler,
    titles_match,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from bioetl.domain.ports import LoggerPort


class ExtendedFallbackHandler(BaseAlternateIdFallbackHandler):
    """Handles fallback search by title and alternate ID (PMID).

    Extends fallback logic to support 4-phase strategy including PMID lookup.
    """

    def __init__(
        self,
        logger: LoggerPort,
        search_fn: Callable[[str, int], Any],
        alternate_search_fn: Callable[[str], Any],
    ) -> None:
        """Initialize extended fallback handler.

        Args:
            logger: Logger port.
            search_fn: Async function to search works by title.
            alternate_search_fn: Async function to search works by PMID.
        """
        super().__init__(logger, provider_prefix="openalex")
        self._search_fn = search_fn
        self._alternate_search_fn = alternate_search_fn

    async def _search_by_title(self, title: str) -> dict[str, Any] | None:
        """Search for work by title (reused logic)."""
        candidates = await self._search_fn(title, 3)
        if not candidates:
            return None

        # Iterate through candidates to find a match
        for result in candidates:
            found_title = result.get("title", "")
            if found_title and titles_match(title, found_title):
                return cast("dict[str, Any]", result)

        # Fallback: check if any candidate has no title (rare edge case)
        # Only return if we haven't found a match yet
        for result in candidates:
            if not result.get("title"):
                return cast("dict[str, Any]", result)

        return None

    async def _search_by_alternate_id(self, alt_id: str) -> dict[str, Any] | None:
        """Search for work by PMID."""
        return await self._alternate_search_fn(alt_id)


class TitleFallbackHandler(BaseTitleFallbackHandler):
    """Handles fallback search by title when DOI lookup fails.

    Extracts fallback logic to reduce main class size and cyclomatic complexity.
    Uses title matching to validate search results and reduce false positives.
    Uses provider_prefix="openalex" for auto-generated event names.
    """

    def __init__(
        self,
        logger: LoggerPort,
        search_fn: Callable[[str, int], Any],  # Coroutine returning list[dict]
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
                return cast("dict[str, Any]", result)

        # Fallback: check if any candidate has no title (rare edge case)
        # Only return if we haven't found a match yet
        for result in candidates:
            if not result.get("title"):
                return cast("dict[str, Any]", result)

        return None
