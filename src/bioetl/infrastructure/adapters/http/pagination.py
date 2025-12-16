"""Pagination utilities for HTTP clients.

Provides a reusable mixin for handling common pagination patterns
(cursor-based, offset-based, etc.) over an UnifiedHTTPClient.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any, Protocol, TypeVar

from httpx import Response

T = TypeVar("T")
Params = dict[str, Any]


class FetcherProtocol(Protocol):
    """Protocol for classes that support pagination via UnifiedHTTPClient."""

    http_client: Any  # UnifiedHTTPClient


class PaginatedFetcherMixin:
    """Mixin for implementing paginated fetching logic.

    Requires the host class to have a `http_client` attribute.
    """

    async def fetch_paginated(
        self: FetcherProtocol,
        url: str,
        initial_params: Params,
        extract_items: Callable[[Response], list[T]],
        next_page_params: Callable[[Response, Params], Params | None],
        limit: int | None = None,
        method: str = "GET",
    ) -> AsyncIterator[T]:
        """Generic paginated fetcher.

        Args:
            url: The endpoint URL.
            initial_params: Initial query parameters.
            extract_items: Function to extract list of items from response.
            next_page_params: Function to determine params for next page (or None to stop).
            limit: Maximum total items to yield.
            method: HTTP method (GET/POST).

        Yields:
            Items of type T.
        """
        params = initial_params
        total_yielded = 0
        should_continue = True

        while should_continue:
            if method == "GET":
                response = await self.http_client.get(url, params=params)
            elif method == "POST":
                # Some APIs use POST for search with params in body
                response = await self.http_client.post(url, json=params)
            else:
                raise ValueError(f"Unsupported method: {method}")

            items = extract_items(response)
            if not items:
                break

            for item in items:
                yield item
                total_yielded += 1
                if limit and total_yielded >= limit:
                    return

            # Determine next page
            next_params = next_page_params(response, params)
            if next_params:
                params = next_params
            else:
                should_continue = False
