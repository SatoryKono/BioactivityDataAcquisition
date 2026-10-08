"""Pagination abstraction for HTTP adapters.

Provides PaginatedFetcherMixin to standardize loop logic for offset/cursor based APIs.
"""

from __future__ import annotations

__all__ = ["PaginatedFetcherMixin", "PaginationTruncatedError", "T"]


from collections.abc import AsyncIterator, Awaitable, Callable, Hashable, Mapping
from typing import TYPE_CHECKING, NoReturn, TypeVar

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort

T = TypeVar("T")
CursorT = TypeVar("CursorT", bound=Hashable)


class PaginationTruncatedError(RuntimeError):
    """Signal that pagination stopped before the provider reported exhaustion."""

    def __init__(self, *, reason: str, page_count: int, page_limit: int) -> None:
        self.reason = reason
        self.page_count = page_count
        self.page_limit = page_limit
        super().__init__(
            f"pagination truncated: reason={reason}, page_count={page_count}, "
            f"page_limit={page_limit}"
        )


def raise_pagination_truncated(
    logger: LoggerPort,
    *,
    event: str,
    reason: str,
    page_count: int,
    page_limit: int,
    cursor_field: str,
    cursor_value: object,
    log_context: Mapping[str, object] | None = None,
) -> NoReturn:
    """Log structured truncation evidence and fail the incomplete scan."""
    fields = dict(log_context or {})
    fields.update(reason=reason, page_count=page_count, page_limit=page_limit)
    fields[cursor_field] = cursor_value
    logger.warning(event, **fields)
    raise PaginationTruncatedError(
        reason=reason,
        page_count=page_count,
        page_limit=page_limit,
    )


class PaginatedFetcherMixin:
    """Mixin for implementing standardized pagination logic in HTTP adapters."""

    # Hard ceiling against runaway providers (cursor loops / empty pages).
    _DEFAULT_MAX_PAGES: int = 10_000
    _logger: LoggerPort

    async def _fetch_page_and_check_cursor(
        self,
        page: Awaitable[tuple[list[T], CursorT | None]],
        *,
        seen_cursors: set[CursorT | None],
    ) -> tuple[list[T], CursorT | None, bool]:
        """Fetch a page and defer repeated-cursor handling until after its yield."""
        items, next_cursor = await page
        if next_cursor is None:
            return items, None, False
        if next_cursor in seen_cursors:
            return items, next_cursor, True
        seen_cursors.add(next_cursor)
        return items, next_cursor, False

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
            [CursorT | None, int],
            Awaitable[tuple[list[T], CursorT | None]],
        ],
        limit: int | None = None,
        initial_cursor: CursorT | None = None,
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
        seen_cursors: set[CursorT | None] = (
            {initial_cursor} if initial_cursor is not None else set()
        )
        page_limit = max_pages if max_pages is not None else self._DEFAULT_MAX_PAGES
        if page_limit < 1:
            raise ValueError(f"max_pages must be >= 1, got {page_limit!r}")

        while not self._should_stop_fetching(fetched, limit):
            if page_count >= page_limit:
                raise_pagination_truncated(
                    self._logger,
                    event="pagination_truncated",
                    reason="max_pages",
                    page_count=page_count,
                    page_limit=page_limit,
                    cursor_field="next_cursor",
                    cursor_value=repr(cursor),
                )
            page_count += 1

            items, next_cursor, repeated_cursor = await self._fetch_page_and_check_cursor(
                fetch_func(cursor, fetched),
                seen_cursors=seen_cursors,
            )

            for item in items:
                yield item
                fetched += 1
                if self._should_stop_fetching(fetched, limit):
                    return

            if repeated_cursor:
                raise_pagination_truncated(
                    self._logger,
                    event="pagination_truncated",
                    reason="repeated_cursor",
                    page_count=page_count,
                    page_limit=page_limit,
                    cursor_field="next_cursor",
                    cursor_value=repr(next_cursor),
                )
            if next_cursor is None:
                break
            cursor = next_cursor
