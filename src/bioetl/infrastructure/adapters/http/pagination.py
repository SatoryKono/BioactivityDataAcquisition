"""Pagination abstraction for HTTP adapters.

Provides PaginatedFetcherMixin to standardize loop logic for offset/cursor based APIs.
"""

from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any, Protocol, TypeVar

T = TypeVar("T")


class PageFetcher(Protocol[T]):
    """Protocol for the fetch function passed to paginated_fetch."""

    async def __call__(
        self, cursor: Any | None, fetched: int
    ) -> tuple[list[T], Any | None]:
        """Fetch a page of items.

        Args:
            cursor: The cursor/offset for the next page.
            fetched: Number of items already fetched (for adaptive page sizing).

        Returns:
            A tuple containing:
                - List of items fetched.
                - Next cursor (or None if no more pages).
        """
        ...


class PaginatedFetcherMixin:
    """Mixin for implementing standardized pagination logic in HTTP adapters."""

    @staticmethod
    def _should_stop_fetching(fetched: int, limit: int | None) -> bool:
        """Check if we've reached the global fetch limit."""
        return limit is not None and fetched >= limit

    async def paginated_fetch(
        self,
        fetch_func: Callable[[Any | None, int], Awaitable[tuple[list[T], Any | None]]],
        limit: int | None = None,
        initial_cursor: Any | None = None,
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
