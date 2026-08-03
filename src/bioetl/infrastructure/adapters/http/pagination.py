"""Pagination abstraction for HTTP adapters.

Provides PaginatedFetcherMixin to standardize loop logic for offset/cursor based APIs.
"""

from __future__ import annotations

__all__ = ["PaginatedFetcherMixin", "T"]


from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any, TypeVar

T = TypeVar("T")


class PaginatedFetcherMixin:
    """Mixin for implementing standardized pagination logic in HTTP adapters."""

    @staticmethod
    def _should_stop_fetching(fetched: int, limit: int | None) -> bool:
        """Check if we've reached the global fetch limit.

        Args:
            fetched: Number of items fetched so far.
            limit: Maximum items to fetch, or None for no limit.

        Returns:
            True if the limit is set and the fetched count has reached or exceeded it.
        """
        return limit is not None and fetched >= limit

    async def paginated_fetch(
        self,
        fetch_func: Callable[
            [Any | None, int],  # Any: pagination cursor type varies by API
            Awaitable[
                tuple[list[T], Any | None]  # Any: pagination cursor type varies by API
            ],  # Any: pagination cursor type varies by API
        ],  # Any: cursor type varies per API
        limit: int | None = None,
        initial_cursor: Any | None = None,  # Any: cursor type varies per...
    ) -> AsyncIterator[T]:
        """Fetch all pages using the provided fetch function.

        This method encapsulates the common 'while has_next' loop pattern.

        Args:
            fetch_func: Async callable that takes (cursor, fetched_count)
                        and returns (items, next_cursor).
            limit: Maximum number of items to yield globally across all pages.
            initial_cursor: Starting cursor value (default: None).

        Yields:
            Items from the pages as they are fetched.

        Returns:
            Iterator over results.
        """
        fetched = 0
        cursor = initial_cursor

        while not self._should_stop_fetching(fetched, limit):
            items, next_cursor = await fetch_func(cursor, fetched)

            if not items and next_cursor is None:
                break

            for item in items:
                yield item
                fetched += 1
                if self._should_stop_fetching(fetched, limit):
                    return

            if next_cursor is None:
                break
            cursor = next_cursor
