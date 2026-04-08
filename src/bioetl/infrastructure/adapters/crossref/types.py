"""Public structural protocols for CrossRef runtime collaborators."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from bioetl.domain.types import BronzeRecord

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

__all__ = ["CrossRefBatchFetcher", "CrossRefSearchPaginator"]


class CrossRefBatchFetcher(Protocol):
    """Protocol for DOI batch-fetch collaborators used by CrossRef runtime wiring."""

    def fetch_batch(self, dois: list[str]) -> AsyncIterator[BronzeRecord]:
        """Return an async iterator of CrossRef records for the provided DOIs."""


class CrossRefSearchPaginator(Protocol):
    """Protocol for cursor-based search collaborators used by CrossRef runtime wiring."""

    def search(
        self,
        query: str,
        limit: int | None = None,
        cursor: str = "*",
    ) -> AsyncIterator[BronzeRecord]:
        """Return an async iterator of CrossRef records for the given query."""
