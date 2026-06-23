"""Fallback search utilities for PubMed publication resolution.

Provides title-based search fallback when PMID lookup fails.
Supports three-phase fallback strategy:
- Phase 2: Title fallback for unresolved PMIDs
- Phase 3: Title-only lookup for entries without PMIDs
"""

from __future__ import annotations

__all__ = ["PUBMED_FALLBACK_ERRORS", "PubMedTitleFallbackHandler"]

from typing import TYPE_CHECKING

from httpx import RequestError

from bioetl.domain.exceptions import BioETLError, NetworkError
from bioetl.infrastructure.adapters.common import BaseTitleFallbackHandler, titles_match

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from bioetl.domain.ports import LoggerPort
from bioetl.domain.types import JsonDict

PUBMED_FALLBACK_ERRORS = (
    BioETLError,
    NetworkError,
    RequestError,
    OSError,
    ValueError,
    TypeError,
    RuntimeError,
    KeyError,
)


class PubMedTitleFallbackHandler(BaseTitleFallbackHandler):
    """Handles fallback search by title when PMID/DOI lookup fails.

    Uses PubMed esearch API with title field search:
    term="Title text"[Title]
    Uses provider_prefix="pubmed" for auto-generated event names.
    """

    def __init__(
        self,
        logger: LoggerPort,
        search_fn: Callable[
            [str, int],
            Awaitable[list[JsonDict]],
        ],
    ) -> None:
        """Initialize fallback handler.

        Args:
            logger: Logger port for structured logging.
            search_fn: Async function to search publications by title.
                Callable[[str, int], Awaitable[list[JsonDict]]] with signature
                search_fn(title: str, limit: int) -> list[dict].
        """
        super().__init__(logger, provider_prefix="pubmed")
        self._search_fn = search_fn

    async def _search_by_title(
        self, title: str
    ) -> JsonDict | None:  # Any: untyped API JSON record
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

        except PUBMED_FALLBACK_ERRORS as e:
            self._logger.debug(
                "pubmed_title_search_failed",
                title=clean_title[:50],
                error=str(e),
            )

        return None

    def _get_result_identifier(
        self,
        result: JsonDict,  # Any: untyped API JSON record
    ) -> tuple[str, str]:  # Any: untyped API JSON record
        """Return PubMed PMID for logging.

        Args:
            result: BronzeRecord or raw API dict from the search response.

        Returns:
            Tuple of (field name string, PMID value string) for structured log output.
        """
        return ("found_pmid", str(result.get("pmid", "unknown")))
