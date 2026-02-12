"""Tests for OpenAlex ExtendedFallbackHandler."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.infrastructure.adapters.openalex.fallback import ExtendedFallbackHandler


@pytest.fixture
def mock_logger():
    return MagicMock()


@pytest.fixture
def mock_search_fn():
    return AsyncMock()


@pytest.fixture
def mock_alternate_search_fn():
    return AsyncMock()


@pytest.fixture
def handler(mock_logger, mock_search_fn, mock_alternate_search_fn):
    return ExtendedFallbackHandler(
        logger=mock_logger,
        search_fn=mock_search_fn,
        alternate_search_fn=mock_alternate_search_fn,
    )


@pytest.mark.asyncio
async def test_search_by_title_delegates(handler, mock_search_fn):
    """Test title search delegates to underlying implementation."""
    mock_search_fn.return_value = [{"title": "Test Title", "id": "W1"}]

    result = await handler._search_by_title("Test Title")

    assert result == {"title": "Test Title", "id": "W1"}
    mock_search_fn.assert_called_once()


@pytest.mark.asyncio
async def test_search_by_alternate_id_calls_fn(handler, mock_alternate_search_fn):
    """Test alternate ID search calls the provided function."""
    mock_alternate_search_fn.return_value = {"id": "W1"}

    result = await handler._search_by_alternate_id("12345")

    assert result == {"id": "W1"}
    mock_alternate_search_fn.assert_called_once_with("12345")


@pytest.mark.asyncio
async def test_process_missing_by_alternate_id_flow(handler, mock_alternate_search_fn):
    """Test the full flow of alternate ID processing."""
    ids = ["doi1"]
    found_ids = set()
    alternate_id_mapping = {"doi1": "pmid1"}
    mock_alternate_search_fn.return_value = {"id": "W1"}

    results = []
    async for res in handler.process_missing_by_alternate_id(
        ids, found_ids, alternate_id_mapping, lambda x: x, limit=None, fetched=0
    ):
        results.append(res)

    assert len(results) == 1
    assert results[0]["_alternate_id"] == "pmid1"
    assert "doi1" in found_ids  # Should be updated
