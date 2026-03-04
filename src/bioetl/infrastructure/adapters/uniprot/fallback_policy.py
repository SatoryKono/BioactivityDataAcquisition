"""UniProt fallback policy hooks for shared three-phase orchestration."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable

from bioetl.domain.types import BronzeRecord

__all__ = ["UniProtFallbackPolicyHandler"]


class UniProtFallbackPolicyHandler:
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
        """Process unresolved primary IDs via UniProt fallback lookup."""
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
        """Process title-only marker entries (legacy empty-ID fallback keys)."""
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
        fallback_ids: list[str] = []
        seen_ids: set[str] = set()
        for entry in entries:
            fallback_id = entry if entry in fallback_mapping else ""
            if fallback_id not in fallback_mapping:
                continue
            if fallback_id in seen_ids:
                continue
            seen_ids.add(fallback_id)
            fallback_ids.append(fallback_id)
        return fallback_ids
