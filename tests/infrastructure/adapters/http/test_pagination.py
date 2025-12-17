"""Tests for PaginatedFetcherMixin."""

import pytest
from unittest.mock import Mock

from bioetl.infrastructure.adapters.http.pagination import PaginatedFetcherMixin


class MockFetcher(PaginatedFetcherMixin):
    pass


@pytest.mark.asyncio
async def test_paginated_fetch_basic():
    """Test basic pagination without limit."""
    fetcher = MockFetcher()

    # Page 1: [1, 2], next='c2'
    # Page 2: [3, 4], next=None

    async def fetch_page(cursor, fetched):
        if cursor is None:
            return [1, 2], 'c2'
        elif cursor == 'c2':
            return [3, 4], None
        return [], None

    results = []
    async for item in fetcher.paginated_fetch(fetch_page):
        results.append(item)

    assert results == [1, 2, 3, 4]


@pytest.mark.asyncio
async def test_paginated_fetch_with_limit():
    """Test pagination with limit."""
    fetcher = MockFetcher()

    async def fetch_page(cursor, fetched):
        # Always return 2 items
        val = fetched + 1
        return [val, val + 1], 'next'

    results = []
    async for item in fetcher.paginated_fetch(fetch_page, limit=3):
        results.append(item)

    assert results == [1, 2, 3]


@pytest.mark.asyncio
async def test_paginated_fetch_empty():
    """Test fetching empty results."""
    fetcher = MockFetcher()

    async def fetch_page(cursor, fetched):
        return [], None

    results = []
    async for item in fetcher.paginated_fetch(fetch_page):
        results.append(item)

    assert results == []


@pytest.mark.asyncio
async def test_paginated_fetch_empty_page_with_cursor():
    """Test empty page but valid cursor (should stop if handled conservatively or continue).
    Current implementation stops if items are empty AND cursor is None.
    If items empty but cursor exists, it continues.
    """
    fetcher = MockFetcher()

    count = 0
    async def fetch_page(cursor, fetched):
        nonlocal count
        count += 1
        if count == 1:
            return [], 'c2' # Empty page but has next
        if count == 2:
            return [1], None
        return [], None

    results = []
    async for item in fetcher.paginated_fetch(fetch_page):
        results.append(item)

    assert results == [1]


@pytest.mark.asyncio
async def test_paginated_fetch_passes_fetched_count():
    """Test that fetched count is passed correctly."""
    fetcher = MockFetcher()

    fetched_values = []

    async def fetch_page(cursor, fetched):
        fetched_values.append(fetched)
        if fetched < 4:
            return [1, 1], 'next'
        return [], None

    async for _ in fetcher.paginated_fetch(fetch_page):
        pass

    # Initial: 0. Returns 2.
    # Next: 2. Returns 2.
    # Next: 4. Returns empty.
    assert fetched_values == [0, 2, 4]
