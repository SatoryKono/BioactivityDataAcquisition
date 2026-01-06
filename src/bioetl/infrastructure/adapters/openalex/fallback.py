"""Fallback search utilities for OpenAlex DOI resolution.

Provides title-based search fallback when DOI resolution fails.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from bioetl.infrastructure.adapters.common import BaseTitleFallbackHandler

if TYPE_CHECKING:
    from collections.abc import Callable

    from bioetl.domain.ports import LoggerPort


class TitleFallbackHandler(BaseTitleFallbackHandler):
    """Handles fallback search by title when DOI lookup fails.

    Extracts fallback logic to reduce main class size and cyclomatic complexity.
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
        super().__init__(logger)
        self._search_fn = search_fn

    @property
    def _event_no_fallback_title(self) -> str:
        """Return log event name for missing fallback title."""
        return "openalex_no_fallback_title"

    @property
    def _event_fallback_attempt(self) -> str:
        """Return log event name for fallback attempt."""
        return "openalex_title_fallback_attempt"

    @property
    def _event_fallback_success(self) -> str:
        """Return log event name for successful fallback."""
        return "openalex_title_fallback_success"

    @property
    def _event_fallback_not_found(self) -> str:
        """Return log event name for failed fallback."""
        return "openalex_title_fallback_not_found"

    async def _search_by_title(self, title: str) -> dict[str, Any] | None:
        """Search for work by title using OpenAlex API.

        Args:
            title: Publication title to search for.

        Returns:
            Work record if found, None otherwise.
        """
        result = await self._search_fn(title, 3)
        return cast(dict[str, Any] | None, result)

    def _get_result_identifier(self, result: dict[str, Any]) -> tuple[str, str]:
        """Return OpenAlex work ID for logging."""
        return ("found_id", str(result.get("id", "unknown")))

    def _process_found_result(
        self, result: dict[str, Any], original_doi: str
    ) -> dict[str, Any]:
        """Add lookup method metadata to found work.

        Args:
            result: The found work record.
            original_doi: The DOI that was originally searched.

        Returns:
            Work with _lookup_method and _original_doi added.
        """
        result["_lookup_method"] = "title_fallback"
        result["_original_doi"] = original_doi
        return result
