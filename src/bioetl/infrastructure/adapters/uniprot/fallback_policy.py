"""UniProt fallback policy hooks for shared three-phase orchestration."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable

from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.adapters.common.deduplication import (
    deduplicate_preserving_order,
)

__all__ = ["UniProtFallbackPolicy"]


class UniProtFallbackPolicy:
    """Adapter-specific fallback hooks for UniProt fetch orchestration."""

    def __init__(
        self,
        *,
        entity_type: str,
        resolve_missing_ids: Callable[
            [list[str], set[str], dict[str, str]],
            list[str],
        ],
        search_fallback: Callable[
            [str, list[str], dict[str, str], int | None, int],
            AsyncIterator[BronzeRecord],
        ],
    ) -> None:
        """Initialize UniProt fallback policy handler.

        Args:
            entity_type: Entity type identifier for the adapter
                (e.g., "protein", "gene").
            resolve_missing_ids: Callable that resolves which primary IDs still
                need fetching after the main batch. Signature:
                ``(dois, found_dois, fallback_mapping) -> missing_ids``.
            search_fallback: Async callable that fetches records for a list of
                missing IDs. Signature:
                ``(entity_type, ids, fallback_mapping, limit, fetched) -> AsyncIterator``.

        """
        self._entity_type = entity_type
        self._resolve_missing_ids = resolve_missing_ids
        self._search_fallback = search_fallback

    async def process_missing_dois(
        self,
        *,
        dois: list[str],
        found_dois: set[str],
        fallback_mapping: dict[str, str],
        normalize_fn: Callable[[str], str | None],
        limit: int | None,
        fetched: int,
    ) -> AsyncIterator[BronzeRecord]:
        """Process unresolved primary IDs via UniProt fallback lookup.

        Resolves which IDs are still missing after the main batch fetch, then
        delegates to the injected ``search_fallback`` callable.

        Args:
            dois: Full list of requested primary IDs.
            found_dois: Set of IDs already successfully fetched.
            fallback_mapping: Mapping from ID to fallback identifier (e.g., gene name).
            normalize_fn: Callable to normalise an ID string; unused for UniProt
                (UniProt uses exact IDs, not normalised DOIs).
            limit: Maximum total records to yield (None means unlimited).
            fetched: Count of records already yielded before this call.

        Yields:
            Bronze records resolved via UniProt fallback search.

        """
        del normalize_fn
        missing_ids = self._resolve_missing_ids(dois, found_dois, fallback_mapping)
        if not missing_ids:
            return
        async for record in self._search_fallback(
            self._entity_type,
            missing_ids,
            fallback_mapping,
            limit,
            fetched,
        ):
            yield record

    async def process_title_only_entries(
        self,
        *,
        entries: list[str],
        fallback_mapping: dict[str, str],
        limit: int | None,
        fetched: int,
    ) -> AsyncIterator[BronzeRecord]:
        """Process title-only marker entries (legacy empty-ID fallback keys).

        Collects unique fallback IDs from the entry list and delegates to
        ``search_fallback`` for retrieval.

        Args:
            entries: List of entry markers (empty strings or ``__title_only_N__``).
            fallback_mapping: Mapping from entry marker to fallback ID string.
            limit: Maximum total records to yield (None means unlimited).
            fetched: Count of records already yielded before this call.

        Yields:
            Bronze records resolved via UniProt fallback search.

        """
        fallback_ids = self._collect_title_only_fallback_ids(entries, fallback_mapping)
        if not fallback_ids:
            return
        async for record in self._search_fallback(
            self._entity_type,
            fallback_ids,
            fallback_mapping,
            limit,
            fetched,
        ):
            yield record

    @staticmethod
    def _collect_title_only_fallback_ids(
        entries: list[str],
        fallback_mapping: dict[str, str],
    ) -> list[str]:
        return deduplicate_preserving_order(
            entry for entry in entries if entry in fallback_mapping
        )
