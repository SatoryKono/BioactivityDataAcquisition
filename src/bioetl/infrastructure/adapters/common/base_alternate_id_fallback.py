"""Base fallback handler for alternate ID resolution.

Provides common utilities for fallback search using alternate identifiers
(e.g., PMID for DOI pipelines, or DOI for PMID pipelines).
"""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any

from bioetl.infrastructure.adapters.common.base_title_fallback import (
    BaseTitleFallbackHandler,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable


class BaseAlternateIdFallbackHandler(BaseTitleFallbackHandler):
    """Base class for alternate ID fallback search handlers.

    Extends BaseTitleFallbackHandler to add Phase 2: Alternate ID lookup.

    4-Phase Strategy:
        Phase 1: Primary batch lookup - implemented by adapter
        Phase 2: Alternate ID lookup - process_missing_by_alternate_id()
        Phase 3: Title fallback - process_missing_dois()
        Phase 4: Title-only - process_title_only_entries()

    Event Naming Convention:
        Extends base convention with:
        - {provider}_alternate_id_fallback_attempt
        - {provider}_alternate_id_fallback_success
        - {provider}_alternate_id_fallback_not_found
        - {provider}_no_alternate_id
    """

    @property
    def _event_no_alternate_id(self) -> str:
        """Return log event name for missing alternate ID."""
        if self._provider_prefix:
            return f"{self._provider_prefix}_no_alternate_id"
        return "no_alternate_id"

    @property
    def _event_alternate_id_attempt(self) -> str:
        """Return log event name for alternate ID lookup attempt."""
        if self._provider_prefix:
            return f"{self._provider_prefix}_alternate_id_fallback_attempt"
        return "alternate_id_fallback_attempt"

    @property
    def _event_alternate_id_success(self) -> str:
        """Return log event name for successful alternate ID lookup."""
        if self._provider_prefix:
            return f"{self._provider_prefix}_alternate_id_fallback_success"
        return "alternate_id_fallback_success"

    @property
    def _event_alternate_id_not_found(self) -> str:
        """Return log event name for failed alternate ID lookup."""
        if self._provider_prefix:
            return f"{self._provider_prefix}_alternate_id_fallback_not_found"
        return "alternate_id_fallback_not_found"

    @abstractmethod
    async def _search_by_alternate_id(self, alt_id: str) -> dict[str, Any] | None:
        """Search for publication by alternate identifier.

        Args:
            alt_id: Alternate identifier to search for (e.g., PMID).

        Returns:
            Publication record if found, None otherwise.
        """
        ...

    def _process_alternate_id_result(
        self, result: dict[str, Any], original_id: str, alt_id: str
    ) -> dict[str, Any]:
        """Process found result before yielding.

        Args:
            result: The found publication record.
            original_id: The original primary ID.
            alt_id: The alternate ID used for lookup.

        Returns:
            Processed result with metadata added.
        """
        result["_lookup_method"] = "alternate_id_fallback"
        result["_original_id"] = original_id
        result["_alternate_id"] = alt_id
        return result

    async def process_missing_by_alternate_id(
        self,
        ids: list[str],
        found_ids: set[str],
        alternate_id_mapping: dict[str, str],
        normalize_fn: Callable[[str], str | None],
        limit: int | None,
        fetched: int,
    ) -> AsyncIterator[dict[str, Any]]:
        """Process IDs not found via batch fetch using alternate ID fallback.

        Phase 2 of the 4-phase fallback strategy.

        Args:
            ids: List of primary IDs that were requested.
            found_ids: Set of IDs that were successfully resolved.
            alternate_id_mapping: Mapping {primary_id: alternate_id}.
            normalize_fn: Function to normalize primary ID strings.
            limit: Maximum total records to return.
            fetched: Number of records already fetched.

        Yields:
            Publication records found via alternate ID search.
        """
        for id_val in ids:
            if limit and fetched >= limit:
                return

            normalized_id = (normalize_fn(id_val) or "").lower()
            if normalized_id in found_ids:
                continue

            # Try to get alternate ID
            alt_id = alternate_id_mapping.get(id_val)
            if not alt_id:
                # Also try lookup by normalized ID if different
                if normalized_id and normalized_id != id_val.lower():
                    alt_id = alternate_id_mapping.get(normalized_id)

            if not alt_id:
                self._logger.debug(self._event_no_alternate_id, id=id_val)
                continue

            self._logger.info(
                self._event_alternate_id_attempt,
                id=id_val,
                alternate_id=alt_id,
            )

            result = await self._search_by_alternate_id(alt_id)
            if result:
                id_field, id_value = self._get_result_identifier(result)
                self._logger.info(
                    self._event_alternate_id_success,
                    original_id=id_val,
                    alternate_id=alt_id,
                    **{id_field: id_value},
                )
                yield self._process_alternate_id_result(result, id_val, alt_id)
                fetched += 1

                # Mark as found to avoid subsequent fallbacks
                found_ids.add(normalized_id)
            else:
                self._logger.warning(
                    self._event_alternate_id_not_found,
                    id=id_val,
                    alternate_id=alt_id,
                )
