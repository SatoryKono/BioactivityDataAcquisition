"""Pagination abstraction for HTTP adapters.

Provides PaginatedFetcherMixin to standardize loop logic for offset/cursor based APIs.
"""

from __future__ import annotations

__all__ = ["PaginatedFetcherMixin", "T"]


from collections.abc import AsyncIterator, Awaitable, Callable
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort

T = TypeVar("T")


class PaginatedFetcherMixin:
    """Mixin for implementing standardized pagination logic in HTTP adapters."""

    # Hard ceiling against runaway providers (cursor loops / empty pages).
    _DEFAULT_MAX_PAGES: int = 10_000
    _logger: LoggerPort

    def _log_pagination_truncation(
        self, *, reason: str, page_count: int, page_limit: int, next_cursor: object
    ) -> None:
        """Report abnormal termination through the host's injected logger."""
        self._logger.warning(
            "pagination_truncated",
            truncation_reason=reason,
            page_count=page_count,
            page_limit=page_limit,
            next_cursor=repr(next_cursor),
        )

    def _advance_or_report_truncation(
        self,
        *,
        next_cursor: object,
        seen_cursors: set[object],
        page_count: int,
        page_limit: int,
    ) -> object | None:
        """Advance a cursor, reporting repeats without marking clean exhaustion."""
        advanced = self._advance_pagination_cursor(
            next_cursor=next_cursor, seen_cursors=seen_cursors
        )
        if advanced is None and next_cursor is not None:
            self._log_pagination_truncation(
                reason="repeated_cursor",
                page_count=page_count,
                page_limit=page_limit,
                next_cursor=next_cursor,
            )
        return advanced

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

    def _advance_pagination_cursor(
        self,
        *,
        next_cursor: object,
        seen_cursors: set[object],
    ) -> object | None:
        """Return next cursor or None when pagination should terminate."""
        if next_cursor is None:
            return None
        if next_cursor in seen_cursors:
            return None
        seen_cursors.add(next_cursor)
        return next_cursor

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
        *,
        max_pages: int | None = None,
    ) -> AsyncIterator[T]:
        """Fetch all pages using the provided fetch function.

        This method encapsulates the common 'while has_next' loop pattern.

        Args:
            fetch_func: Async callable that takes (cursor, fetched_count)
                        and returns (items, next_cursor).
            limit: Maximum number of items to yield globally across all pages.
            initial_cursor: Starting cursor value (default: None).
            max_pages: Optional hard page cap (defaults to ``_DEFAULT_MAX_PAGES``).

        Yields:
            Items from the pages as they are fetched.

        Returns:
            Iterator over results.
        """
        fetched = 0
        cursor = initial_cursor
        page_count = 0
        seen_cursors: set[object] = (
            {initial_cursor} if initial_cursor is not None else set()
        )
        page_limit = max_pages if max_pages is not None else self._DEFAULT_MAX_PAGES
        if page_limit < 1:
            raise ValueError(f"max_pages must be >= 1, got {page_limit!r}")

        while not self._should_stop_fetching(fetched, limit):
            if page_count >= page_limit:
                self._log_pagination_truncation(
                    reason="max_pages",
                    page_count=page_count,
                    page_limit=page_limit,
                    next_cursor=cursor,
                )
                break
            page_count += 1

            items, next_cursor = await fetch_func(cursor, fetched)

            if not items and next_cursor is None:
                break

            for item in items:
                yield item
                fetched += 1
                if self._should_stop_fetching(fetched, limit):
                    return

            advanced = self._advance_or_report_truncation(
                next_cursor=next_cursor,
                seen_cursors=seen_cursors,
                page_count=page_count,
                page_limit=page_limit,
            )
            if advanced is None:
                break
            cursor = advanced
