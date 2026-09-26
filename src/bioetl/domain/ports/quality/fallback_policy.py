"""Fallback policy port for three-phase filter lookup orchestration."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from typing import Protocol, runtime_checkable

from bioetl.domain.types import BronzeRecord

__all__ = ["FallbackPolicyPort"]


@runtime_checkable
class FallbackPolicyPort(Protocol):
    """Protocol for provider-specific fallback processing hooks."""

    def process_missing_dois(
        self,
        *,
        dois: list[str],
        found_dois: set[str],
        fallback_mapping: dict[str, str],
        normalize_fn: Callable[[str], str | None],
        limit: int | None,
        fetched: int,
    ) -> AsyncIterator[BronzeRecord]:
        """Yield records for unresolved primary IDs.

        Args:
            dois: All DOIs requested in the current fetch batch.
            found_dois: Set of DOIs already resolved in the primary fetch.
            fallback_mapping: Mapping from DOI to title for fallback title lookup.
            normalize_fn: Callable that normalizes a DOI string or returns None.
            limit: Optional maximum number of total records to yield; None means unlimited.
            fetched: Number of records already fetched before this fallback call.
        """
        ...

    def process_title_only_entries(
        self,
        *,
        entries: list[str],
        fallback_mapping: dict[str, str],
        limit: int | None,
        fetched: int,
    ) -> AsyncIterator[BronzeRecord]:
        """Yield records for title-only marker entries.

        Args:
            entries: List of title-only marker strings to process.
            fallback_mapping: Mapping from marker to title string.
            limit: Optional maximum number of total records to yield; None means unlimited.
            fetched: Number of records already fetched before this fallback call.
        """
        ...
