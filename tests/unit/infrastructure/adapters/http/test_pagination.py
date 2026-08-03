# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Tests for PaginatedFetcherMixin."""

from __future__ import annotations

import asyncio

import pytest

from bioetl.infrastructure.adapters.http.pagination import PaginatedFetcherMixin


class MockFetcher(PaginatedFetcherMixin):
    pass


@pytest.mark.asyncio
async def test_paginated_fetch_basic():
    """Test basic pagination without limit."""
    fetcher = MockFetcher()

    # Page 1: [1, 2], next='c2'
    # Page 2: [3, 4], next=None

    async def fetch_page(cursor, _):
        await asyncio.sleep(0)
        if cursor is None:
            return [1, 2], "c2"
        elif cursor == "c2":
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

    async def fetch_page(cursor, _):
        await asyncio.sleep(0)
        # Always return 2 items
        # Since we don't have 'fetched' count passed in, we use cursor state or internal state
        # But 'cursor' here is just passed back.
        # For this test, we can just return dummy items.
        return [1, 2], "next"

    results = []
    async for item in fetcher.paginated_fetch(fetch_page, limit=3):
        results.append(item)

    # We return [1, 2] repeatedly.
    # 1st page: [1, 2]. Total 2.
    # 2nd page: [1, 2]. Take 1 (limit 3). Total 3.
    # Result: [1, 2, 1]
    assert results == [1, 2, 1]


@pytest.mark.asyncio
async def test_paginated_fetch_empty():
    """Test fetching empty results."""
    fetcher = MockFetcher()

    async def fetch_page(cursor, _):
        await asyncio.sleep(0)
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

    async def fetch_page(cursor, _):
        await asyncio.sleep(0)
        nonlocal count
        count += 1
        if count == 1:
            return [], "c2"  # Empty page but has next
        if count == 2:
            return [1], None
        return [], None

    results = []
    async for item in fetcher.paginated_fetch(fetch_page):
        results.append(item)

    assert results == [1]


# Removed test_paginated_fetch_passes_fetched_count as 'fetched' argument is not supported
