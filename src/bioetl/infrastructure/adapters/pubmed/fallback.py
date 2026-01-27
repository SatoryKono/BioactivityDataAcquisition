"""Fallback search utilities for PubMed publication resolution.

Provides title-based search fallback when PMID lookup fails.
Supports three-phase fallback strategy:
- Phase 2: Title fallback for unresolved PMIDs
- Phase 3: Title-only lookup for entries without PMIDs
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bioetl.infrastructure.adapters.common import BaseTitleFallbackHandler, titles_match

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

    from bioetl.domain.ports import LoggerPort


class TitleFallbackHandler(BaseTitleFallbackHandler):
    """Handles fallback search by title when PMID/DOI lookup fails.

    Uses PubMed esearch API with title field search:
    term="Title text"[Title]
    Uses provider_prefix="pubmed" for auto-generated event names.

    Rate limiting: 0.34s delay between requests (3 req/sec) to comply with
    NCBI E-utilities rate limits (3 requests/second without API key).
    """

    # PubMed/NCBI rate limit: 3 requests/second (without API key)
    SEARCH_DELAY_SECONDS = 0.34

    def __init__(
        self,
        logger: LoggerPort,
        search_fn: Callable[[str, int], Coroutine[Any, Any, list[dict[str, Any]]]],
    ) -> None:
        """Initialize fallback handler.

        Args:
            logger: Logger port for structured logging.
            search_fn: Async function to search publications by title.
                       Signature: search_fn(title: str, limit: int) -> list[dict]
        """
        super().__init__(
            logger,
            provider_prefix="pubmed",
            search_delay_seconds=self.SEARCH_DELAY_SECONDS,
        )
        self._search_fn = search_fn

    async def _search_by_title(self, title: str) -> dict[str, Any] | None:
        """Search for publication by title using PubMed esearch.

        Validates results using title matching to reduce false positives.

        Args:
            title: Publication title to search for.

        Returns:
            Publication record if found and title matches, None otherwise.
        """
        # Clean title for search (PubMed practical limit ~200 chars)
        clean_title = title.strip()[:200]

        try:
            results = await self._search_fn(clean_title, 3)

            for publication in results:
                pub_title = publication.get("article_title", "")
                if pub_title and titles_match(clean_title, pub_title):
                    return publication

            # If we got results but no title match, return first result
            # (title may be in different format in PubMed)
            if results:
                return results[0]

        except Exception as e:
            self._logger.debug(
                "pubmed_title_search_failed",
                title=clean_title[:50],
                error=str(e),
            )

        return None

    def _get_result_identifier(self, result: dict[str, Any]) -> tuple[str, str]:
        """Return PubMed PMID for logging."""
        return ("found_pmid", str(result.get("pmid", "unknown")))
