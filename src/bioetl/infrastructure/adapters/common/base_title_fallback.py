"""Base fallback handler for title-based DOI resolution.

Provides common utilities for fallback search across different providers.
Supports three-phase fallback strategy:
- Phase 1: Batch ID lookup (implemented by adapter)
- Phase 2: Title fallback for unresolved IDs (process_missing_dois)
- Phase 3: Title-only lookup for entries without IDs (process_title_only_entries)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable

    from bioetl.domain.ports import LoggerPort


class BaseTitleFallbackHandler(ABC):
    """Base class for title-based fallback search handlers.

    Provides common utilities for fallback title lookup when DOI resolution fails.
    Subclasses implement provider-specific search logic.

    Three-Phase Fallback Strategy:
        Phase 1: Batch ID lookup - implemented by adapter
        Phase 2: Title fallback - process_missing_dois() for unresolved IDs
        Phase 3: Title-only - process_title_only_entries() for empty IDs
    """

    def __init__(self, logger: LoggerPort) -> None:
        """Initialize base fallback handler.

        Args:
            logger: Logger port for structured logging.
        """
        self._logger = logger

    @property
    @abstractmethod
    def _event_no_fallback_title(self) -> str:
        """Return log event name for missing fallback title."""
        ...

    @property
    @abstractmethod
    def _event_fallback_attempt(self) -> str:
        """Return log event name for fallback attempt."""
        ...

    @property
    @abstractmethod
    def _event_fallback_success(self) -> str:
        """Return log event name for successful fallback."""
        ...

    @property
    @abstractmethod
    def _event_fallback_not_found(self) -> str:
        """Return log event name for failed fallback."""
        ...

    @property
    def _event_title_only_attempt(self) -> str:
        """Return log event name for title-only lookup attempt.

        Override in subclass to customize event name.
        Default implementation returns '{provider}_title_only_attempt'.
        """
        return "title_only_attempt"

    @property
    def _event_title_only_success(self) -> str:
        """Return log event name for successful title-only lookup.

        Override in subclass to customize event name.
        """
        return "title_only_success"

    @property
    def _event_title_only_not_found(self) -> str:
        """Return log event name for failed title-only lookup.

        Override in subclass to customize event name.
        """
        return "title_only_not_found"

    @abstractmethod
    async def _search_by_title(self, title: str) -> dict[str, Any] | None:
        """Search for publication by title.

        Args:
            title: Publication title to search for.

        Returns:
            Publication record if found, None otherwise.
        """
        ...

    def _get_result_identifier(self, result: dict[str, Any]) -> tuple[str, str]:
        """Return (field_name, value) for logging the found result.

        Args:
            result: The found publication record.

        Returns:
            Tuple of (log_field_name, identifier_value).
        """
        return ("found_id", str(result.get("id", "unknown")))

    def _process_found_result(
        self, result: dict[str, Any], original_doi: str
    ) -> dict[str, Any]:
        """Process found result before yielding.

        Override to add metadata like _lookup_method.

        Args:
            result: The found publication record.
            original_doi: The DOI that was originally searched.

        Returns:
            Processed result (may be modified or returned as-is).
        """
        return result

    def _get_fallback_title(
        self, doi: str, normalized_doi: str | None, fallback_mapping: dict[str, str]
    ) -> str | None:
        """Get fallback title for a DOI from mapping.

        Args:
            doi: Original DOI string.
            normalized_doi: Normalized DOI string (lowercase, without URL prefix).
            fallback_mapping: Mapping from DOI to title.

        Returns:
            Title if found in mapping, None otherwise.
        """
        if normalized_doi:
            return fallback_mapping.get(doi) or fallback_mapping.get(normalized_doi)
        return fallback_mapping.get(doi)

    def _truncate_title(self, title: str, max_len: int = 50) -> str:
        """Truncate title for logging.

        Args:
            title: Title to truncate.
            max_len: Maximum length before truncation.

        Returns:
            Truncated title with ellipsis if needed.
        """
        return title[:max_len] + "..." if len(title) > max_len else title

    async def process_missing_dois(
        self,
        dois: list[str],
        found_dois: set[str],
        fallback_mapping: dict[str, str],
        normalize_fn: Callable[[str], str | None],
        limit: int | None,
        fetched: int,
    ) -> AsyncIterator[dict[str, Any]]:
        """Process DOIs not found via batch fetch using title fallback.

        Args:
            dois: List of DOIs that were requested.
            found_dois: Set of DOIs that were successfully resolved (lowercase).
            fallback_mapping: Mapping {doi: title} for fallback search.
            normalize_fn: Function to normalize DOI strings.
            limit: Maximum total records to return.
            fetched: Number of records already fetched.

        Yields:
            Publication records found via title search.
        """
        for doi in dois:
            if limit and fetched >= limit:
                return

            normalized_doi = (normalize_fn(doi) or "").lower()
            if normalized_doi in found_dois:
                continue

            title = self._get_fallback_title(doi, normalized_doi, fallback_mapping)
            if not title:
                self._logger.debug(self._event_no_fallback_title, doi=doi)
                continue

            self._logger.info(
                self._event_fallback_attempt,
                doi=doi,
                title=self._truncate_title(title),
            )

            result = await self._search_by_title(title)
            if result:
                id_field, id_value = self._get_result_identifier(result)
                self._logger.info(
                    self._event_fallback_success,
                    original_doi=doi,
                    title=title[:50],
                    **{id_field: id_value},
                )
                yield self._process_found_result(result, doi)
                fetched += 1
            else:
                self._logger.warning(
                    self._event_fallback_not_found,
                    doi=doi,
                    title=title[:50],
                )

    def _process_title_only_result(self, result: dict[str, Any]) -> dict[str, Any]:
        """Process title-only result before yielding.

        Override to add metadata like _lookup_method.
        Default implementation adds _lookup_method = "title_only".

        Args:
            result: The found publication record.

        Returns:
            Processed result with _lookup_method added.
        """
        result["_lookup_method"] = "title_only"
        return result

    async def process_title_only_entries(
        self,
        entries: list[str],
        fallback_mapping: dict[str, str],
        limit: int | None,
        fetched: int,
    ) -> AsyncIterator[dict[str, Any]]:
        """Process entries without primary ID (title-only lookup).

        Phase 3 of the three-phase fallback strategy. Handles entries
        where no DOI was provided, using only the title for lookup.

        Args:
            entries: List of empty/placeholder entries (typically empty strings).
            fallback_mapping: Mapping {entry: title} for lookup.
                Also checks fallback_mapping.get("") as fallback.
            limit: Maximum total records to return.
            fetched: Number of records already fetched.

        Yields:
            Publication records found via title search.
        """
        for entry in entries:
            if limit and fetched >= limit:
                return

            # Try entry key first, then empty string fallback
            title = fallback_mapping.get(entry, fallback_mapping.get(""))
            if not title:
                continue

            self._logger.info(
                self._event_title_only_attempt,
                title=self._truncate_title(title),
            )

            result = await self._search_by_title(title)
            if result:
                id_field, id_value = self._get_result_identifier(result)
                self._logger.info(
                    self._event_title_only_success,
                    title=title[:50],
                    **{id_field: id_value},
                )
                yield self._process_title_only_result(result)
                fetched += 1
            else:
                self._logger.debug(
                    self._event_title_only_not_found,
                    title=title[:50],
                )
