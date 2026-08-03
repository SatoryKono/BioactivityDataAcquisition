"""Fallback search utilities for CrossRef DOI resolution.

Provides title-based search fallback when DOI resolution fails.
Supports three-phase fallback strategy:
- Phase 2: Title fallback for unresolved DOIs
- Phase 3: Title-only lookup for entries without DOIs
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.infrastructure.adapters.common import BaseTitleFallbackHandler, titles_match
from bioetl.infrastructure.adapters.common.error_bundles import (
    COMMON_TITLE_FALLBACK_ERRORS,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable

    from bioetl.domain.ports import LoggerPort
from bioetl.domain.types import JsonDict

CROSSREF_FALLBACK_ERRORS = COMMON_TITLE_FALLBACK_ERRORS


# Re-export titles_match for backwards compatibility
__all__ = ["CrossRefTitleFallbackHandler", "titles_match"]


class CrossRefTitleFallbackHandler(BaseTitleFallbackHandler):
    """Handles fallback search by title when DOI lookup fails.

    Extracts fallback logic to reduce main class size and cyclomatic complexity.
    Uses provider_prefix="crossref" for auto-generated event names.
    """

    def __init__(
        self,
        logger: LoggerPort,
        search_fn: Callable[
            [str, int], AsyncIterator[JsonDict]  # Any: untyped API JSON record
        ],  # Any: untyped API JSON record
    ) -> None:
        """Initialize fallback handler.

        Args:
            logger: Logger port for structured logging.
            search_fn: Async function to search publications by query.
        """
        super().__init__(logger, provider_prefix="crossref")
        self._search_fn = search_fn

    def _get_result_identifier(
        self,
        result: JsonDict,  # Any: untyped API JSON record
    ) -> tuple[str, str]:  # Any: untyped API JSON record
        """Return CrossRef DOI for logging.

        Args:
            result: BronzeRecord or raw API dict from the search response.

        Returns:
            Tuple of (field name string, DOI value string) for structured log output.
        """
        return ("found_doi", str(result.get("DOI", "unknown")))

    async def _search_by_title(
        self, title: str
    ) -> JsonDict | None:  # Any: untyped API JSON record
        """Search for a publication by title.

        Args:
            title: Publication title to search for.

        Returns:
            First relevant publication or None.
        """
        return await self.search_by_title(title)

    async def search_by_title(
        self,
        title: str,
        limit: int = 3,
    ) -> JsonDict | None:  # Any: untyped API JSON record
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
        except CROSSREF_FALLBACK_ERRORS as e:
            self._logger.debug(
                "crossref_title_search_failed",
                title=clean_title[:50],
                error=str(e),
            )

        return None
