"""Fallback policy port for three-phase filter lookup orchestration."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from typing import runtime_checkable

from typing_extensions import Protocol

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
        """Yield records for unresolved primary IDs."""
        ...

    def process_title_only_entries(
        self,
        *,
        entries: list[str],
        fallback_mapping: dict[str, str],
        limit: int | None,
        fetched: int,
    ) -> AsyncIterator[BronzeRecord]:
        """Yield records for title-only marker entries."""
        ...
