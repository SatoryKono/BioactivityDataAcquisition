"""Base fallback handler for title-based DOI resolution.

Provides common utilities for fallback search across different providers.
Supports three-phase fallback strategy:
- Phase 1: Batch ID lookup (implemented by adapter)
- Phase 2: Title fallback for unresolved IDs (process_missing_dois)
- Phase 3: Title-only lookup for entries without IDs (process_title_only_entries)

Rate limiting is enforced between title search requests to comply with
provider API limits (e.g., OpenAlex 10 req/sec, CrossRef 50 req/sec).
"""

from __future__ import annotations

import asyncio
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

    Event Naming Convention:
        When provider_prefix is set, event names are auto-generated:
        - {provider}_no_fallback_title
        - {provider}_title_fallback_attempt
        - {provider}_title_fallback_success
        - {provider}_title_fallback_not_found
        - {provider}_title_only_attempt
        - {provider}_title_only_success
        - {provider}_title_only_not_found

        Subclasses can override individual event properties if needed.
    """

    def __init__(
        self,
        logger: LoggerPort,
        *,
        provider_prefix: str | None = None,
        search_delay_seconds: float = 0.1,
    ) -> None:
        """Initialize base fallback handler.

        Args:
            logger: Logger port for structured logging.
            provider_prefix: Provider name prefix for auto-generating event names.
                If provided, default event properties use this prefix.
                Example: provider_prefix="crossref" generates
                    "crossref_title_fallback_attempt" etc.
            search_delay_seconds: Delay between title search requests in seconds.
                Used for rate limiting. Default 0.1s (10 req/sec).
                Set to 0 to disable rate limiting.
        """
        self._logger = logger
        self._provider_prefix = provider_prefix
        self._search_delay_seconds = search_delay_seconds

    @property
    def _event_no_fallback_title(self) -> str:
        """Return log event name for missing fallback title.

        Default: '{provider}_no_fallback_title' if provider_prefix is set.
        """
        if self._provider_prefix:
            return f"{self._provider_prefix}_no_fallback_title"
        return "no_fallback_title"

    @property
    def _event_fallback_attempt(self) -> str:
        """Return log event name for fallback attempt.

        Default: '{provider}_title_fallback_attempt' if provider_prefix is set.
        """
        if self._provider_prefix:
            return f"{self._provider_prefix}_title_fallback_attempt"
        return "title_fallback_attempt"

    @property
    def _event_fallback_success(self) -> str:
        """Return log event name for successful fallback.

        Default: '{provider}_title_fallback_success' if provider_prefix is set.
        """
        if self._provider_prefix:
            return f"{self._provider_prefix}_title_fallback_success"
        return "title_fallback_success"

    @property
    def _event_fallback_not_found(self) -> str:
        """Return log event name for failed fallback.

        Default: '{provider}_title_fallback_not_found' if provider_prefix is set.
        """
        if self._provider_prefix:
            return f"{self._provider_prefix}_title_fallback_not_found"
        return "title_fallback_not_found"

    @property
    def _event_title_only_attempt(self) -> str:
        """Return log event name for title-only lookup attempt.

        Default: '{provider}_title_only_attempt' if provider_prefix is set.
        """
        if self._provider_prefix:
            return f"{self._provider_prefix}_title_only_attempt"
        return "title_only_attempt"

    @property
    def _event_title_only_success(self) -> str:
        """Return log event name for successful title-only lookup.

        Default: '{provider}_title_only_success' if provider_prefix is set.
        """
        if self._provider_prefix:
            return f"{self._provider_prefix}_title_only_success"
        return "title_only_success"

    @property
    def _event_title_only_not_found(self) -> str:
        """Return log event name for failed title-only lookup.

        Default: '{provider}_title_only_not_found' if provider_prefix is set.
        """
        if self._provider_prefix:
            return f"{self._provider_prefix}_title_only_not_found"
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

        Default implementation adds standard metadata fields:
        - _lookup_method = "title_fallback"
        - _original_id = original_doi

        Override to customize or extend.

        Args:
            result: The found publication record.
            original_doi: The DOI that was originally searched.

        Returns:
            Processed result with _lookup_method and _original_id added.
        """
        result["_lookup_method"] = "title_fallback"
        result["_original_id"] = original_doi
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

            # Rate limiting between title search requests
            if self._search_delay_seconds > 0:
                await asyncio.sleep(self._search_delay_seconds)

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

        Supports two entry formats:
        - Empty strings "" (legacy): looks up fallback_mapping.get("")
        - Markers "__title_only_N__": looks up fallback_mapping.get(marker)

        Args:
            entries: List of entries - empty strings or __title_only_N__ markers.
            fallback_mapping: Mapping {entry: title} for lookup.
                Supports both marker keys and empty string fallback.
            limit: Maximum total records to return.
            fetched: Number of records already fetched.

        Yields:
            Publication records found via title search.
        """
        for entry in entries:
            if limit and fetched >= limit:
                return

            # Try entry key first (supports __title_only_N__ markers),
            # then empty string fallback for legacy compatibility
            title = fallback_mapping.get(entry, fallback_mapping.get(""))
            if not title:
                continue

            self._logger.info(
                self._event_title_only_attempt,
                title=self._truncate_title(title),
                marker=entry if entry.startswith("__title_only_") else None,
            )

            result = await self._search_by_title(title)

            # Rate limiting between title search requests
            if self._search_delay_seconds > 0:
                await asyncio.sleep(self._search_delay_seconds)

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
