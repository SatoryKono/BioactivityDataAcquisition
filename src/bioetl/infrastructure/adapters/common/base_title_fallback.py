"""Base fallback handler for title-based DOI resolution.

Provides common utilities for fallback search across different providers.
Supports three-phase fallback strategy:
- Phase 1: Batch ID lookup (implemented by adapter)
- Phase 2: Title fallback for unresolved IDs (process_missing_dois)
- Phase 3: Title-only lookup for entries without IDs (process_title_only_entries)
"""

from __future__ import annotations

__all__ = ["BaseTitleFallbackHandler"]


from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable

    from bioetl.domain.ports import LoggerPort
from bioetl.domain.types import JsonDict


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
        self, logger: LoggerPort, *, provider_prefix: str | None = None
    ) -> None:
        """Initialize base fallback handler.

        Args:
            logger: Logger port for structured logging.
            provider_prefix: Provider name prefix for auto-generating event names.
                If provided, default event properties use this prefix.
                Example: provider_prefix="crossref" generates
                    "crossref_title_fallback_attempt" etc.
        """
        self._logger = logger
        self._provider_prefix = provider_prefix

    def _event_name(self, suffix: str, default: str) -> str:
        """Return provider-scoped event name or default."""
        if self._provider_prefix:
            return f"{self._provider_prefix}_{suffix}"
        return default

    @property
    def _event_no_fallback_title(self) -> str:
        return self._event_name("no_fallback_title", "no_fallback_title")

    @property
    def _event_fallback_attempt(self) -> str:
        return self._event_name("title_fallback_attempt", "title_fallback_attempt")

    @property
    def _event_fallback_success(self) -> str:
        return self._event_name("title_fallback_success", "title_fallback_success")

    @property
    def _event_fallback_not_found(self) -> str:
        return self._event_name(
            "title_fallback_not_found",
            "title_fallback_not_found",
        )

    @property
    def _event_title_only_attempt(self) -> str:
        return self._event_name("title_only_attempt", "title_only_attempt")

    @property
    def _event_title_only_success(self) -> str:
        return self._event_name("title_only_success", "title_only_success")

    @property
    def _event_title_only_not_found(self) -> str:
        return self._event_name("title_only_not_found", "title_only_not_found")

    @abstractmethod
    async def _search_by_title(
        self, title: str
    ) -> JsonDict | None:  # Any: untyped API response data
        """Search for publication by title.

        Args:
            title: Publication title to search for.

        Returns:
            Publication record if found, None otherwise.
        """
        ...

    def _get_result_identifier(
        self,
        result: JsonDict,  # Any: untyped API response
    ) -> tuple[str, str]:
        """Return (field_name, value) for logging the found result.

        Args:
            result: The found publication record.

        Returns:
            Tuple of (log_field_name, identifier_value).
        """
        return ("found_id", str(result.get("id", "unknown")))

    def _process_found_result(
        self,
        result: JsonDict,  # Any: untyped API response
        original_doi: str,
    ) -> JsonDict:  # Any: untyped API response
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
    ) -> AsyncIterator[JsonDict]:  # Any: untyped API response data
        """Resolve unfetched DOIs via title fallback search.

        Phase 2 of the three-phase fallback strategy. For each DOI not already
        present in ``found_dois``, looks up a candidate title in
        ``fallback_mapping`` and calls ``_search_by_title`` to retrieve the
        record from the provider.

        Args:
            dois: Ordered list of DOIs to attempt fallback resolution for.
            found_dois: Set of already-resolved normalised DOIs to skip.
            fallback_mapping: Mapping from DOI (or normalised DOI) to title string.
            normalize_fn: Callable that normalises a DOI string; may return None.
            limit: Maximum total records to yield (None means unlimited).
            fetched: Count of records already yielded before this call.

        Yields:
            Publication records resolved via title search.

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

    def _process_title_only_result(
        self,
        result: JsonDict,  # Any: untyped API response
    ) -> JsonDict:  # Any: untyped API response
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
    ) -> AsyncIterator[JsonDict]:  # Any: untyped API response data
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

        Returns:
            Processed result.
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
