"""Unit tests for CrossRef batch processing utilities.

Tests for DoiBatchProcessor and SearchPaginator classes.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import RequestError

from bioetl.infrastructure.adapters.crossref.batch import (
    DoiBatchProcessor,
    SearchPaginator,
)
from bioetl.infrastructure.adapters.crossref.exceptions import CrossRefApiError


@pytest.fixture
def mock_http():
    """Create a mock HTTP transport."""
    return AsyncMock()


@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    return MagicMock()


@pytest.fixture
def mock_metrics():
    """Create mock metrics with context manager."""
    metrics = MagicMock()
    metrics.measure_request.return_value.__enter__ = MagicMock()
    metrics.measure_request.return_value.__exit__ = MagicMock()
    return metrics


@pytest.fixture
def batch_processor(mock_http, mock_logger, mock_metrics):
    """Create a DoiBatchProcessor instance."""
    return DoiBatchProcessor(
        http=mock_http,
        logger=mock_logger,
        metrics=mock_metrics,
        mailto="test@example.com",
        api_base="https://api.crossref.org",
        headers_fn=lambda: {"User-Agent": "Test"},
    )


@pytest.fixture
def search_paginator(mock_http, mock_logger, mock_metrics):
    """Create a SearchPaginator instance."""
    return SearchPaginator(
        http=mock_http,
        logger=mock_logger,
        metrics=mock_metrics,
        mailto="test@example.com",
        api_base="https://api.crossref.org",
        headers_fn=lambda: {"User-Agent": "Test"},
    )


# =============================================================================
# DoiBatchProcessor Tests
# =============================================================================


@pytest.mark.asyncio
async def test_fetch_single_success(batch_processor, mock_http):
    """Test successful single DOI fetch."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "message": {
            "DOI": "10.1038/nature12373",
            "title": ["Test Title"],
        }
    }
    mock_http.get.return_value = mock_response

    result = await batch_processor.fetch_single("10.1038/nature12373")

    assert result is not None
    assert result["DOI"] == "10.1038/nature12373"


@pytest.mark.asyncio
async def test_fetch_single_not_found(batch_processor, mock_http, mock_logger):
    """Test single DOI fetch returns None on 404."""
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_http.get.return_value = mock_response

    result = await batch_processor.fetch_single("10.1234/nonexistent")

    assert result is None
    mock_logger.debug.assert_called_with(
        "crossref_doi_not_found", doi="10.1234/nonexistent"
    )


@pytest.mark.asyncio
async def test_fetch_single_api_error(batch_processor, mock_http):
    """Test single DOI fetch raises on non-404 error."""
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_http.get.return_value = mock_response

    with pytest.raises(CrossRefApiError):
        await batch_processor.fetch_single("10.1038/nature12373")


@pytest.mark.asyncio
async def test_fetch_single_network_error(batch_processor, mock_http):
    """Test single DOI fetch raises on network error."""
    mock_http.get.side_effect = RequestError("Network error")

    with pytest.raises(CrossRefApiError, match="Failed to fetch DOI"):
        await batch_processor.fetch_single("10.1038/nature12373")


@pytest.mark.asyncio
async def test_fetch_batch_success(batch_processor, mock_http):
    """Test successful batch DOI fetch."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "message": {
            "items": [
                {"DOI": "10.1038/nature12373", "title": ["Title 1"]},
                {"DOI": "10.1016/j.cell.2019.03.025", "title": ["Title 2"]},
            ]
        }
    }
    mock_http.get.return_value = mock_response

    results = []
    async for item in batch_processor.fetch_batch(
        ["10.1038/nature12373", "10.1016/j.cell.2019.03.025"]
    ):
        results.append(item)

    assert len(results) == 2
    assert results[0]["DOI"] == "10.1038/nature12373"
    assert results[1]["DOI"] == "10.1016/j.cell.2019.03.025"


@pytest.mark.asyncio
async def test_fetch_batch_ignores_non_mapping_items(batch_processor, mock_http):
    """Only mapping-shaped items should be yielded as BronzeRecord values."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "message": {
            "items": [
                {"DOI": "10.1038/nature12373", "title": ["Title 1"]},
                "unexpected-string-item",
                123,
            ]
        }
    }
    mock_http.get.return_value = mock_response

    results = []
    async for item in batch_processor.fetch_batch(["10.1038/nature12373"]):
        results.append(item)

    assert results == [{"DOI": "10.1038/nature12373", "title": ["Title 1"]}]


@pytest.mark.asyncio
async def test_fetch_batch_empty_list(batch_processor):
    """Test batch fetch with empty DOI list."""
    results = []
    async for item in batch_processor.fetch_batch([]):
        results.append(item)

    assert len(results) == 0


@pytest.mark.asyncio
async def test_fetch_batch_falls_back_on_error(batch_processor, mock_http, mock_logger):
    """Test batch fetch falls back to individual on HTTP error."""
    # First call (batch) fails with 500
    batch_response = MagicMock()
    batch_response.status_code = 500

    # Second call (individual) succeeds
    single_response = MagicMock()
    single_response.status_code = 200
    single_response.json.return_value = {
        "message": {"DOI": "10.1038/nature12373", "title": ["Title"]}
    }

    mock_http.get.side_effect = [batch_response, single_response]

    results = []
    async for item in batch_processor.fetch_batch(["10.1038/nature12373"]):
        results.append(item)

    # Should have logged warning and fallen back
    mock_logger.warning.assert_called_with(
        "crossref_batch_fetch_failed", status_code=500, doi_count=1
    )
    assert len(results) == 1


@pytest.mark.asyncio
async def test_fetch_batch_falls_back_on_exception(
    batch_processor, mock_http, mock_logger
):
    """Test batch fetch falls back on network exception."""
    # First call (batch) raises exception
    single_response = MagicMock()
    single_response.status_code = 200
    single_response.json.return_value = {
        "message": {"DOI": "10.1038/nature12373", "title": ["Title"]}
    }

    mock_http.get.side_effect = [
        RequestError("Network error"),
        single_response,
    ]

    results = []
    async for item in batch_processor.fetch_batch(["10.1038/nature12373"]):
        results.append(item)

    mock_logger.warning.assert_called()
    assert len(results) == 1


# =============================================================================
# SearchPaginator Tests
# =============================================================================


@pytest.mark.asyncio
async def test_search_success(search_paginator, mock_http):
    """Test successful search with results."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "message": {
            "items": [
                {"DOI": "10.1038/nature12373", "title": ["Title 1"]},
                {"DOI": "10.1016/j.cell.2019.03.025", "title": ["Title 2"]},
            ],
            "next-cursor": None,
        }
    }
    mock_http.get.return_value = mock_response

    results = []
    async for item in search_paginator.search("rhodopsin", limit=10):
        results.append(item)

    assert len(results) == 2


@pytest.mark.asyncio
async def test_search_with_limit(search_paginator, mock_http):
    """Test search respects limit parameter."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "message": {
            "items": [{"DOI": f"10.1234/test{i}"} for i in range(10)],
            "next-cursor": "cursor123",
        }
    }
    mock_http.get.return_value = mock_response

    results = []
    async for item in search_paginator.search("test", limit=3):
        results.append(item)

    assert len(results) == 3


@pytest.mark.asyncio
async def test_search_pagination(search_paginator, mock_http):
    """Test search handles pagination correctly."""
    # First page
    page1_response = MagicMock()
    page1_response.status_code = 200
    page1_response.json.return_value = {
        "message": {
            "items": [{"DOI": f"10.1234/page1_{i}"} for i in range(3)],
            "next-cursor": "cursor_page2",
        }
    }

    # Second page (last)
    page2_response = MagicMock()
    page2_response.status_code = 200
    page2_response.json.return_value = {
        "message": {
            "items": [{"DOI": f"10.1234/page2_{i}"} for i in range(2)],
            "next-cursor": None,
        }
    }

    mock_http.get.side_effect = [page1_response, page2_response]

    results = []
    async for item in search_paginator.search("test"):
        results.append(item)

    assert len(results) == 5
    assert mock_http.get.call_count == 2


@pytest.mark.asyncio
async def test_search_stops_on_empty_page(search_paginator, mock_http):
    """Test search stops when page has no items."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "message": {
            "items": [],
            "next-cursor": "cursor123",
        }
    }
    mock_http.get.return_value = mock_response

    results = []
    async for item in search_paginator.search("test"):
        results.append(item)

    assert len(results) == 0
    assert mock_http.get.call_count == 1


@pytest.mark.asyncio
async def test_search_invalid_message_body_raises_api_error(
    search_paginator, mock_http
):
    """Non-mapping message payloads should fail with a typed CrossRefApiError."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"message": "invalid"}
    mock_http.get.return_value = mock_response

    with pytest.raises(CrossRefApiError, match="invalid response body"):
        results = []
        async for item in search_paginator.search("test"):
            results.append(item)


@pytest.mark.asyncio
async def test_search_stops_on_same_cursor(search_paginator, mock_http):
    """Test search stops when cursor doesn't change (infinite loop prevention)."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "message": {
            "items": [{"DOI": "10.1234/test"}],
            "next-cursor": "*",  # Same as initial cursor
        }
    }
    mock_http.get.return_value = mock_response

    results = []
    async for item in search_paginator.search("test", cursor="*"):
        results.append(item)

    assert len(results) == 1
    assert mock_http.get.call_count == 1


@pytest.mark.asyncio
async def test_search_api_error(search_paginator, mock_http):
    """Test search raises on API error."""
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_http.get.return_value = mock_response

    with pytest.raises(CrossRefApiError, match="CrossRef search failed"):
        async for _ in search_paginator.search("test"):
            continue


@pytest.mark.asyncio
async def test_search_network_error(search_paginator, mock_http, mock_logger):
    """Test search raises on network error."""
    mock_http.get.side_effect = RequestError("Network error")

    with pytest.raises(CrossRefApiError, match="CrossRef search failed"):
        async for _ in search_paginator.search("test"):
            continue

    mock_logger.error.assert_called_once()


@pytest.mark.asyncio
async def test_should_continue_pagination_logic(search_paginator):
    """Test pagination continuation logic."""
    # Empty items - should stop
    assert (
        search_paginator._should_continue_pagination([], "cursor2", "cursor1") is False
    )

    # No next cursor - should stop
    assert (
        search_paginator._should_continue_pagination([{"DOI": "test"}], None, "cursor1")
        is False
    )

    # Same cursor - should stop
    assert (
        search_paginator._should_continue_pagination(
            [{"DOI": "test"}], "cursor1", "cursor1"
        )
        is False
    )

    # Different cursor with items - should continue
    assert (
        search_paginator._should_continue_pagination(
            [{"DOI": "test"}], "cursor2", "cursor1"
        )
        is True
    )
